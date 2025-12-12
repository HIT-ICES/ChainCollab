import React, { useState, useEffect } from 'react';
import type { ChangeEvent } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TableContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TextField,
  Paper,
  IconButton
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import type { DmnDefinition, UploadableDmn } from '@/types/modeler';

interface UploadDmnModalProps {
  dmnData: Map<string, DmnDefinition>;
  open: boolean;
  setOpen: (open: boolean) => void;
  onUpload: (items: UploadableDmn[]) => Promise<void> | void;
}

const UploadDmnModal: React.FC<UploadDmnModalProps> = ({
  dmnData,
  open,
  setOpen,
  onUpload
}) => {

  const [data, setData] = useState<UploadableDmn[]>([]);

  useEffect(() => {
    if (!dmnData) {
      setData([]);
      return;
    }
    const formattedData: UploadableDmn[] = Array.from(dmnData.entries()).map(([id, value]) => ({
      id,
      name: value.name ?? id,
      uploadName: value.name ?? id,
      dmnContent: value.dmnContent,
      svgContent: value.svgContent
    }));
    setData(formattedData);
  }, [dmnData]);

  const handleOk = async () => {
    const validItems = data.filter((item) => item.uploadName?.trim().length);
    if (validItems.length) {
      await onUpload(validItems);
    }
    setOpen(false);
  };

  const handleCancel = () => setOpen(false);

  const handleInputChange = (index: number, event: ChangeEvent<HTMLInputElement>) => {
    const newData = [...data];
    newData[index] = {
      ...newData[index],
      uploadName: event.target.value
    };
    setData(newData);
  };

  return (
    <Dialog open={open} onClose={handleCancel} fullWidth maxWidth="md">
      <DialogTitle
        sx={{ fontWeight: 600, display: "flex", justifyContent: "space-between", alignItems: "center" }}
      >
        Upload Dmns
        <IconButton onClick={handleCancel} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers sx={{ background: "#f8fafc" }}>
        <TableContainer component={Paper} elevation={0} sx={{ borderRadius: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Upload Name</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((item, index) => (
                <TableRow key={item.id}>
                  <TableCell>{item.id}</TableCell>
                  <TableCell>{item.name}</TableCell>
                  <TableCell>
                    <TextField
                      fullWidth
                      size="small"
                      value={item.uploadName}
                      onChange={(event) => handleInputChange(index, event as ChangeEvent<HTMLInputElement>)}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </DialogContent>
      <DialogActions
        sx={{ borderTop: "1px solid #e2e8f0", background: "#fff" }}
      >
        <Button onClick={handleCancel}>Cancel</Button>
        <Button onClick={handleOk} variant="contained" disabled={!data.length}>
          Upload
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default UploadDmnModal;
