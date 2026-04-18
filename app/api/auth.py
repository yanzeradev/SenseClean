from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.core.security import verify_password, get_password_hash, create_access_token
from fastapi.security import OAuth2PasswordBearer
import jwt
from app.core.security import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Schemas de validação para a rota
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Cria um novo cliente no banco de dados."""
    # Verifica se o email já existe
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Este e-mail já está em uso.")
    
    # Cria o usuário com a senha criptografada
    hashed_pw = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Usuário criado com sucesso!"}

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    """Verifica e-mail e senha e devolve o Token JWT."""
    db_user = db.query(User).filter(User.email == user.email).first()
    
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )
    
    # Gera o crachá de acesso contendo o ID do usuário
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "email": db_user.email
    }

    # Diz ao FastAPI onde os clientes pegam o token (usado para gerar a documentação Swagger)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Intercepte a requisição, valida o token e retorna o usuário logado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
        
    return user