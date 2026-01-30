package com.chaincollab.dmn.server.listener;

import com.chaincollab.dmn.server.service.DmnCacheService;
import io.reactivex.disposables.Disposable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.core.DefaultBlockParameterName;
import org.web3j.protocol.core.DefaultBlockParameterNumber;
import org.web3j.protocol.core.methods.request.EthFilter;
import org.web3j.protocol.http.HttpService;
import org.web3j.crypto.Hash;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.math.BigInteger;

@Component
public class OcrTransmissionListener {

    @Value("${ocr.listener.enabled:true}")
    private boolean enabled;

    @Value("${ocr.rpc.url:http://localhost:8545}")
    private String rpcUrl;

    @Value("${ocr.aggregator.address:}")
    private String aggregatorAddress;

    @Autowired
    private DmnCacheService cacheService;

    private Web3j web3j;
    private Disposable subscription;

    private static final String NEW_TRANSMISSION_TOPIC =
        Hash.sha3String("NewTransmission(uint32,int192,address,int192[],bytes,bytes32)");

    @PostConstruct
    public void start() {
        if (!enabled) {
            System.out.println("OCR listener disabled by config (ocr.listener.enabled=false)");
            return;
        }
        if (aggregatorAddress == null || aggregatorAddress.isEmpty()) {
            System.err.println("OCR listener disabled: aggregator address is empty");
            return;
        }
        System.out.println("OCR listener enabled");
        System.out.println("OCR RPC URL: " + rpcUrl);
        System.out.println("OCR aggregator address: " + aggregatorAddress);
        web3j = Web3j.build(new HttpService(rpcUrl));
        EthFilter filter = new EthFilter(
            DefaultBlockParameterName.LATEST,
            DefaultBlockParameterName.LATEST,
            aggregatorAddress
        );
        filter.addSingleTopic(NEW_TRANSMISSION_TOPIC);

        subscription = web3j.ethLogFlowable(filter).subscribe(log -> {
            try {
                BigInteger blockNumber = log.getBlockNumber();
                if (blockNumber == null) {
                    return;
                }
                System.out.println("OCR NewTransmission log received: block=" + blockNumber);
                BigInteger timestamp = web3j.ethGetBlockByNumber(
                    new DefaultBlockParameterNumber(blockNumber), false
                ).send().getBlock().getTimestamp();
                Long blockTimestampMs = timestamp == null ? null : timestamp.longValue() * 1000;
                System.out.println("OCR NewTransmission timestamp(ms): " + blockTimestampMs);
                cacheService.ack(null, blockTimestampMs);
            } catch (Exception e) {
                System.err.println("OCR listener error: " + e.getMessage());
            }
        }, error -> System.err.println("OCR listener subscribe error: " + error.getMessage()));
    }

    @PreDestroy
    public void stop() {
        if (subscription != null && !subscription.isDisposed()) {
            subscription.dispose();
        }
        if (web3j != null) {
            web3j.shutdown();
        }
    }
}
