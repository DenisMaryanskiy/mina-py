from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(..., description="Response message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"message": "Operation completed successfully"}
        }
    )
