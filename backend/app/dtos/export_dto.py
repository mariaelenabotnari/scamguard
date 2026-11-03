"""DTOs for data export quotas and receipts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExportFormat = Literal["csv", "json"]
ExportScope = Literal["clusters", "channels"]
AccountTier = Literal["new_account", "verified_researcher"]


class ExportQuotaDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_tier: AccountTier = Field(..., alias="accountTier")
    max_rows_per_export: int = Field(..., alias="maxRowsPerExport")
    daily_exports_limit: int = Field(..., alias="dailyExportsLimit")
    daily_exports_used: int = Field(..., alias="dailyExportsUsed")


class ExportReceiptDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    file_name: str = Field(..., alias="fileName")
    format: ExportFormat
    scope: ExportScope
    rows_exported: int = Field(..., alias="rowsExported")
    generated_at: str = Field(..., alias="generatedAt")


class TriggerExportInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    scope: ExportScope
    format: ExportFormat
