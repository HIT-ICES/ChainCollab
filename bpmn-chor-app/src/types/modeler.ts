export interface DmnDefinition {
  name: string;
  dmnContent: string;
  svgContent: string;
}

export interface UploadableDmn extends DmnDefinition {
  id: string;
  uploadName: string;
}
