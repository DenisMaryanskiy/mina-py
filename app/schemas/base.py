from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(..., description="Response message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"message": "Operation completed successfully"}
        }
    )


class HTTPErrorResponse(BaseModel):
    """Schema for HTTP error responses."""

    detail: str = Field(..., description="Error detail message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "An error occurred while processing the request"
            }
        }
    )
