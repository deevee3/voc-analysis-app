"""API endpoints for data export."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from voc_app.services.export_service import ExportService

from .dependencies import DatabaseSession

router = APIRouter()


@router.get("/insights/csv")
async def export_insights_csv(
    session: DatabaseSession,
    # Add filter parameters matching insights.py
    feedback_id: str | None = None,
    data_source_id: str | None = None,
    platform: str | None = None,
    sentiment_label: str | None = None,
):
    """Export insights to CSV format.
    
    Returns a CSV file download with filtered insights data.
    """
    try:
        filters = {
            "feedback_id": feedback_id,
            "data_source_id": data_source_id,
            "platform": platform,
            "sentiment_label": sentiment_label,
        }
        
        csv_buffer = await ExportService.export_insights_csv(session, filters)
        
        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=insights_export.csv"
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


@router.get("/insights/json")
async def export_insights_json(
    session: DatabaseSession,
    feedback_id: str | None = None,
    data_source_id: str | None = None,
    platform: str | None = None,
    sentiment_label: str | None = None,
):
    """Export insights to JSON format.
    
    Returns a JSON file download with filtered insights data.
    """
    try:
        filters = {
            "feedback_id": feedback_id,
            "data_source_id": data_source_id,
            "platform": platform,
            "sentiment_label": sentiment_label,
        }
        
        json_data = await ExportService.export_insights_json(session, filters)
        
        return StreamingResponse(
            iter([json_data]),
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=insights_export.json"
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


@router.get("/insights/excel")
async def export_insights_excel(
    session: DatabaseSession,
    feedback_id: str | None = None,
    data_source_id: str | None = None,
    platform: str | None = None,
    sentiment_label: str | None = None,
):
    """Export insights to Excel format.
    
    Returns an Excel file download with filtered insights data.
    Requires openpyxl package to be installed.
    """
    try:
        filters = {
            "feedback_id": feedback_id,
            "data_source_id": data_source_id,
            "platform": platform,
            "sentiment_label": sentiment_label,
        }
        
        excel_buffer = await ExportService.export_insights_excel(session, filters)
        
        return StreamingResponse(
            iter([excel_buffer.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=insights_export.xlsx"
            },
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Excel export requires openpyxl package. Install with: pip install openpyxl",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )
