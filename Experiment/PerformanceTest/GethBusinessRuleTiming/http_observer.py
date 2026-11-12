#!/usr/bin/env python3
"""Read-only packet observer for actual CDMN HTTP/IPFS calls inside its netns.

Run under docker exec, not imported into the application. No proxy, monkeypatch,
configuration change, service restart or synthetic IPFS fetch is involved.
"""
import hashlib
import json
import os
import socket
import struct
import time


def now():return time.monotonic_ns()/1e6


def message(data):
    index=data.find(b'\r\n\r\n')
    if index<0:return None
    lines=data[:index].decode('iso-8859-1').split('\r\n')
    headers={}
    for line in lines[1:]:
        if ':' in line:
            k,v=line.split(':',1);headers[k.lower()]=v.strip()
    body=data[index+4:]
    if 'chunked' in headers.get('transfer-encoding','').lower():
        chunks=[];cursor=0
        while True:
            end=body.find(b'\r\n',cursor)
            if end<0:return None
            size=int(body[cursor:end].split(b';')[0],16);cursor=end+2
            if len(body)<cursor+size+2:return None
            if not size:return lines[0],headers,b''.join(chunks)
            chunks.append(body[cursor:cursor+size]);cursor+=size+2
    length=int(headers.get('content-length','0'))
    if len(body)<length:return None
    return lines[0],headers,body[:length]


class Stream:
    def __init__(self):self.next=None;self.parts={};self.data=b'';self.start=None
    def add(self,seq,payload,at):
        if self.start is None:self.start=at
        if self.next is None:self.next=seq
        if seq<self.next:
            payload=payload[self.next-seq:];seq=self.next
        if not payload:return
        self.parts[seq]=payload
        while self.next in self.parts:
            part=self.parts.pop(self.next);self.data+=part;self.next+=len(part)


def main():
    sock=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(3));sock.bind(('eth0',0))
    connections={}
    print(json.dumps({'type':'ready','pid':os.getpid(),'monotonic_ms':now(),'wall_ms':time.time_ns()/1e6}),flush=True)
    while True:
        packet=sock.recv(65535);at=now()
        if len(packet)<54 or packet[12:14]!=b'\x08\x00':continue
        ip=packet[14:];ihl=(ip[0]&15)*4
        if ip[9]!=6 or len(ip)<ihl+20:continue
        src=socket.inet_ntoa(ip[12:16]);dst=socket.inet_ntoa(ip[16:20])
        tcp=ip[ihl:];sport,dport,seq=struct.unpack('!HHI',tcp[:8]);offset=(tcp[12]>>4)*4
        payload=tcp[offset:struct.unpack('!H',ip[2:4])[0]-ihl]
        if not payload:continue
        direction=(src,sport,dst,dport);reverse=(dst,dport,src,sport)
        is_request=payload.startswith((b'GET ',b'POST '))
        if is_request and (b'/ipfs/' in payload.split(b'\r\n',1)[0] or b'/api/dmn/calc' in payload.split(b'\r\n',1)[0]):
            connections[direction]={'request':Stream(),'response':Stream(),'requestDirection':direction}
        if direction in connections:
            conn=connections[direction];stream=conn['request']
        elif reverse in connections:
            conn=connections[reverse];stream=conn['response']
        else:continue
        stream.add(seq,payload,at)
        try:
            req=message(conn['request'].data)
            res=message(conn['response'].data)
        except (ValueError,UnicodeError):
            connections.pop(conn['requestDirection'],None);continue
        if req and 'requestEnd' not in conn:conn['requestEnd']=at
        if not req or not res:continue
        first,headers,body=req;status,response_headers,output=res
        record={'type':'http','request':first,'status':int(status.split()[1]),
            'start_ms':conn['request'].start,'request_end_ms':conn['requestEnd'],
            'response_start_ms':conn['response'].start,'end_ms':at,
            'request_bytes':len(body),'response_bytes':len(output),
            'response_sha256':hashlib.sha256(output).hexdigest(),
            'source':src,'destination':dst,'wall_ms':time.time_ns()/1e6}
        if '/api/dmn/calc' in first:
            record['kind']='cdmn'
            try:record['input']=json.loads(body);record['output']=json.loads(output)
            except ValueError:record['invalid_json']=True
        else:record['kind']='ipfs';record['cid']=first.split()[1].split('/ipfs/',1)[1].split('?')[0]
        print(json.dumps(record),flush=True)
        connections.pop(conn['requestDirection'],None)


if __name__=='__main__':main()
