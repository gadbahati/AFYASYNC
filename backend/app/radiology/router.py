from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.dependencies import get_db, require_permission
from app.radiology.models import ImagingTest
from app.radiology.schemas import ImagingOrderCreate, ImagingReportCreate, ImagingTestCreate, ImagingOrderResponse, ImagingReportResponse, ImagingTestResponse
from app.radiology.service import create_order, create_test, report_order, review_report
router=APIRouter(prefix="/api/v1/radiology",tags=["Radiology"])

def err(e):
    codes={"PATIENT_NOT_IN_FACILITY":403,"IMAGING_TEST_NOT_FOUND":404,"IMAGING_ORDER_NOT_FOUND":404,"IMAGING_REPORT_NOT_FOUND":404,"IMAGING_ALREADY_COMPLETED":409,"IMAGING_ALREADY_REVIEWED":409,"ENCOUNTER_NOT_OPEN":400}
    return HTTPException(codes.get(str(e),400),detail=str(e))
@router.post("/tests",response_model=ImagingTestResponse,status_code=201)
def tests(payload:ImagingTestCreate,db:Session=Depends(get_db),user=Depends(require_permission("lab.catalogue.write"))): return create_test(db,user.facility_id,user.id,payload)
@router.get("/tests",response_model=list[ImagingTestResponse])
def list_tests(db:Session=Depends(get_db),user=Depends(require_permission("patients.record.read"))): return db.scalars(select(ImagingTest).where(ImagingTest.facility_id==user.facility_id,ImagingTest.active.is_(True)).order_by(ImagingTest.name)).all()
@router.post("/orders",response_model=ImagingOrderResponse,status_code=201)
def orders(payload:ImagingOrderCreate,db:Session=Depends(get_db),user=Depends(require_permission("encounters.create"))):
    try:return create_order(db,user.facility_id,user.id,payload)
    except ValueError as e:raise err(e)
@router.post("/orders/{order_id}/report",response_model=ImagingReportResponse)
def report(order_id:UUID,payload:ImagingReportCreate,db:Session=Depends(get_db),user=Depends(require_permission("encounters.create"))):
    try:return report_order(db,user.facility_id,user.id,order_id,payload)
    except ValueError as e:raise err(e)
@router.post("/reports/{report_id}/review",response_model=ImagingReportResponse)
def review(report_id:UUID,db:Session=Depends(get_db),user=Depends(require_permission("encounters.create"))):
    try:return review_report(db,user.facility_id,user.id,report_id)
    except ValueError as e:raise err(e)
