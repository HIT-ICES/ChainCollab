import DataPaletteProvider from './DataPaletteProvider';
import DataContextPadProvider from './DataContextPadProvider';

export default {
  __init__: ['dataPaletteProvider', 'dataContextPadProvider'],
  dataPaletteProvider: ['type', DataPaletteProvider],
  dataContextPadProvider: ['type', DataContextPadProvider],
};