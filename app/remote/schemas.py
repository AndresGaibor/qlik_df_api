from pydantic import BaseModel


class DataflowRecord(BaseModel):
    dataflow_id: str
    app_id: str = ""
    dataflow_name: str
    description: str = ""
    target_type: str = "target"
    target_id: str = ""
    target_label: str = ""
    filename: str = ""
    extension: str = ""
    format: str = ""
    treat_as_relative: bool = False


class ReplaceDataflowsRequest(BaseModel):
    data: list[DataflowRecord]
