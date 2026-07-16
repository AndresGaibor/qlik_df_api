export type TenantInfo = {
  name: string;
  hostname: string;
};

export type SpaceInfo = {
  name: string;
  id?: string;
};

export type DataflowInfo = {
  name: string;
  type: string;
  href: string;
};

export type QlikRunResult = {
  tenants: TenantInfo[];
  selectedTenant: TenantInfo;
  selectedSpace: SpaceInfo;
  dataflows: DataflowInfo[];
  selectedDataflow: DataflowInfo;
  downloadedFile: string;
};
