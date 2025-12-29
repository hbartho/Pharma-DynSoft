from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from database import db
from auth import require_role
from models.prescription import Prescription, PrescriptionCreate

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])

@router.post("", response_model=Prescription)
async def create_prescription(prescription_data: PrescriptionCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Create a new prescription"""
    prescription_dict = prescription_data.model_dump()
    prescription_dict['tenant_id'] = current_user['tenant_id']
    prescription_obj = Prescription(**prescription_dict)
    
    doc = prescription_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.prescriptions.insert_one(doc)
    return prescription_obj

@router.get("", response_model=List[Prescription])
async def get_prescriptions(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Get all prescriptions"""
    prescriptions = await db.prescriptions.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    for prescription in prescriptions:
        if isinstance(prescription['created_at'], str):
            prescription['created_at'] = datetime.fromisoformat(prescription['created_at'])
    return prescriptions

@router.put("/{prescription_id}/status")
async def update_prescription_status(prescription_id: str, new_status: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Update prescription status"""
    result = await db.prescriptions.update_one(
        {"id": prescription_id, "tenant_id": current_user['tenant_id']},
        {"$set": {"status": new_status}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return {"message": "Prescription updated successfully"}

@router.put("/{prescription_id}/edit", response_model=Prescription)
async def edit_prescription(prescription_id: str, prescription_data: PrescriptionCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Edit a prescription"""
    existing = await db.prescriptions.find_one({"id": prescription_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    update_data = prescription_data.model_dump()
    update_data['tenant_id'] = current_user['tenant_id']
    
    await db.prescriptions.update_one({"id": prescription_id}, {"$set": update_data})
    
    updated_prescription = await db.prescriptions.find_one({"id": prescription_id}, {"_id": 0})
    if isinstance(updated_prescription['created_at'], str):
        updated_prescription['created_at'] = datetime.fromisoformat(updated_prescription['created_at'])
    return Prescription(**updated_prescription)

@router.delete("/{prescription_id}")
async def delete_prescription(prescription_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Delete a prescription"""
    result = await db.prescriptions.delete_one({"id": prescription_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return {"message": "Prescription deleted successfully"}
