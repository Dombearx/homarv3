from pydantic import BaseModel, Field


class CreateProductInput(BaseModel):
    product_name: str = Field(..., description="Name of the product to create.")
    location_name: str = Field(..., description="Grocy location name.")
    quantity_unit_name: str = Field(
        ..., description="Quantity unit name for purchase & stock."
    )
    default_best_before_days_after_open: int = Field(
        0,
        description="Default number of days after opening when the product is considered best before. Use 0 for products that do not require this feature (e.g., vegetables, fruits).",
    )


class AddStockInput(BaseModel):
    product_name: str = Field(..., description="Name of the product to add stock to.")
    amount: float = Field(..., description="Amount of product to add.")
    best_before_date: str = Field(
        default="2999-12-31",
        description="Best before date (YYYY-MM-DD). Defaults to never expiring. Use never expiring only if explicitly told so.",
    )


class ConsumeStockInput(BaseModel):
    product_name: str = Field(..., description="Product name.")
    amount: float = Field(..., description="Amount to consume.")


class OpenStockInput(BaseModel):
    product_name: str = Field(..., description="Product name.")
    amount: float = Field(..., description="Amount to open.")


class ListStockEntriesInput(BaseModel):
    product_name: str = Field(..., description="Product name.")
