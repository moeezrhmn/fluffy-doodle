from fastapi import APIRouter, HTTPException
from app.services.temp_mail_service import *



router = APIRouter(prefix="/temp-mail", tags=["Temp Mail"])


@router.get("/generate-new-email")
async def generate_new_email():
    email = get_new_email()
    return {"email": email, "ttl": get_email_ttl(email)}



@router.get('/is-email-valid')
async def is_email_valid(email: str):
    is_valid = is_email_valids(email)
    ttl = get_email_ttl(email)
    return {"is_valid": is_valid, "ttl": ttl, 'ttl_in_minutes': round(ttl/60, 2)}

@router.post("/get-inbox")
async def get_inbox(email: str):
    """
    Get emails from inbox for the provided email address.
    Validates that the email exists and hasn't expired before checking inbox.
    """
    # First validate that this is a valid temp email
    if not is_email_valid(email):
        raise HTTPException(
            status_code=404,
            detail="Email not found or expired. Please generate a new email."
        )

    

    # For now return placeholder response
    return {
        "email": email,
        "messages": []
    }



@router.get('/get-emails')
async def get_emails(email: str):
    emails = fetch_emails(email)
    return emails