#src.routes.user.py

"""
User routes module.

This module contains the FastAPI routes for user-related operations.
It includes routes for user signup, login, requesting email confirmation,
refreshing tokens, confirming email, updating avatar, and retrieving the current user's information.
"""

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, HTTPException, Depends, status, Security, BackgroundTasks, Request, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.schemas.schemas import UserModel, UserResponse, TokenModel, RequestEmail, UserDb
from src.repository import user as repository_users
from src.conf.config import settings
from src.auth.auth import auth_service
from src.services.email import send_email
from src.models.models import UserDB

# Initialize the router with a prefix and tags for grouping related routes
router = APIRouter(prefix='/auth', tags=["auth"])
security = HTTPBearer()

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: UserModel, background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db)):
    """
    Sign up a new user.

    :param body: The data for the new user.
    :type body: UserModel
    :param background_tasks: Background tasks to be run after the response has been sent.
    :type background_tasks: BackgroundTasks
    :param request: The HTTP request.
    :type request: Request
    :param db: The database session.
    :type db: Session
    :return: The newly created user and a confirmation message.
    :rtype: dict
    :raises HTTPException: If the user already exists.
    """
    exist_user = await repository_users.get_user_by_email(body.email, db)
    if exist_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    body.password = auth_service.get_password_hash(body.password)
    new_user = await repository_users.create_user(body, db)
    background_tasks.add_task(send_email, new_user.email, new_user.username, request.base_url)
    return {"user": new_user, "detail": "User successfully created. Check your email for confirmation."}

@router.post("/login", response_model=TokenModel)
async def login(body: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Log in a user.

    :param body: The OAuth2 password request form.
    :type body: OAuth2PasswordRequestForm
    :param db: The database session.
    :type db: Session
    :return: The access and refresh tokens.
    :rtype: TokenModel
    :raises HTTPException: If the email is invalid, the email is not confirmed, or the password is invalid.
    """
    user = await repository_users.get_user_by_email(body.username, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email")
    if not user.confirmed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed")
    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    # Generate JWT
    access_token = await auth_service.create_access_token(data={"sub": user.email})
    refresh_token = await auth_service.create_refresh_token(data={"sub": user.email})
    await repository_users.update_token(user, refresh_token, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post('/request_email')
async def request_email(body: RequestEmail, background_tasks: BackgroundTasks, request: Request,
                        db: Session = Depends(get_db)):
    """
    Request a new email confirmation.

    :param body: The request email data.
    :type body: RequestEmail
    :param background_tasks: Background tasks to be run after the response has been sent.
    :type background_tasks: BackgroundTasks
    :param request: The HTTP request.
    :type request: Request
    :param db: The database session.
    :type db: Session
    :return: A confirmation message.
    :rtype: dict
    """
    user = await repository_users.get_user_by_email(body.email, db)

    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user:
        background_tasks.add_task(send_email, user.email, user.username, request.base_url)
    return {"message": "Check your email for confirmation."}

@router.get('/refresh_token', response_model=TokenModel)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    """
    Refresh the access token.

    :param credentials: The HTTP authorization credentials.
    :type credentials: HTTPAuthorizationCredentials
    :param db: The database session.
    :type db: Session
    :return: The new access and refresh tokens.
    :rtype: TokenModel
    :raises HTTPException: If the refresh token is invalid.
    """
    token = credentials.credentials
    email = await auth_service.decode_refresh_token(token)
    user = await repository_users.get_user_by_email(email, db)
    if user.refresh_token != token:
        await repository_users.update_token(user, None, db)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = await auth_service.create_access_token(data={"sub": email})
    refresh_token = await auth_service.create_refresh_token(data={"sub": email})
    await repository_users.update_token(user, refresh_token, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get('/confirmed_email/{token}')
async def confirmed_email(token: str, db: Session = Depends(get_db)):
    """
    Confirm the user's email.

    :param token: The confirmation token.
    :type token: str
    :param db: The database session.
    :type db: Session
    :return: A confirmation message.
    :rtype: dict
    :raises HTTPException: If the verification fails.
    """
    email = await auth_service.get_email_from_token(token)
    user = await repository_users.get_user_by_email(email, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error")
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await repository_users.confirmed_email(email, db)
    return {"message": "Email confirmed"}

@router.post("/avatar")
async def update_avatar( file: UploadFile = File(...),
                        current_user: UserDb = Depends(auth_service.get_current_user),
                        db: Session = Depends(get_db),
                    ):
    """
    Update the user's avatar.

    :param file: The uploaded file.
    :type file: UploadFile
    :param current_user: The currently authenticated user.
    :type current_user: UserDb
    :param db: The database session.
    :type db: Session
    :return: A confirmation message and the updated user.
    :rtype: dict
    """
    user = await repository_users.update_avatar( current_user.email, file.filename, db)
    return {"message": "Avatar updated successfully", "user": user}

@router.get("/me/", response_model=UserDb)
async def read_users_me(current_user: UserDB = Depends(auth_service.get_current_user)):
    """
    Retrieve the current user's information.

    :param current_user: The currently authenticated user.
    :type current_user: UserDB
    :return: The current user's information.
    :rtype: UserDb
    """
    return current_user


@router.patch('/avatar', response_model=UserDb)
async def update_avatar_user(file: UploadFile = File(), current_user: UserDB = Depends(auth_service.get_current_user),
                             db: Session = Depends(get_db)):
    """
    Update the user's avatar using Cloudinary.
    Using the service Cloudinary
    
    :param file: The uploaded file.
    :type file: UploadFile
    :param current_user: The currently authenticated user.
    :type current_user: UserDB
    :param db: The database session.
    :type db: Session
    :return: The updated user.
    :rtype: UserDb
    """
    cloudinary.config(
        cloud_name=settings.cloudinary_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True
    )

    r = cloudinary.uploader.upload(file.file, public_id=f'ContactsApp/{current_user.username}', overwrite=True)
    src_url = cloudinary.CloudinaryImage(f'ContactsApp/{current_user.username}')\
                        .build_url(width=250, height=250, crop='fill', version=r.get('version'))
    user = await repository_users.update_avatar(current_user.email, src_url, db)
    return user
