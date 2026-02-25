# gateway/main.py
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse, Response
import httpx
from typing import Any, Optional
from pydantic import BaseModel

# JWT
import jwt
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Logging middleware
import time
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="API Gateway", version="1.0.0")

SERVICES = {
    "student": "http://127.0.0.1:8001",
    "course": "http://127.0.0.1:8002",
}

JWT_SECRET = "CHANGE_THIS_SECRET"  
JWT_ALG = "HS256"
security = HTTPBearer()


def create_access_token(payload: dict, minutes: int = 30) -> str:
    data = payload.copy()
    data["exp"] = datetime.utcnow() + timedelta(minutes=minutes)
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALG)


def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = creds.credentials
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@app.post("/auth/login")
def login(username: str, password: str):
    if username == "admin" and password == "admin123":
        token = create_access_token({"sub": username})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/password")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        ms = (time.time() - start) * 1000
        print(f"[GATEWAY] {request.method} {request.url.path} -> {response.status_code} ({ms:.2f}ms)")
        return response


app.add_middleware(RequestLoggingMiddleware)

async def forward_request(service: str, path: str, method: str, **kwargs) -> Any:
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")

    url = f"{SERVICES[service]}{path}"

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            if method == "GET":
                r = await client.get(url, **kwargs)
            elif method == "POST":
                r = await client.post(url, **kwargs)
            elif method == "PUT":
                r = await client.put(url, **kwargs)
            elif method == "DELETE":
                r = await client.delete(url, **kwargs)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")

            ct = (r.headers.get("content-type") or "").lower()

            if "application/json" in ct:
    
                if r.text.strip() == "":
                    return JSONResponse(content=None, status_code=r.status_code)
                return JSONResponse(content=r.json(), status_code=r.status_code)

            return Response(
                content=r.content,
                status_code=r.status_code,
                media_type=ct.split(";")[0] if ct else None
            )

        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail=f"{service} service unavailable (connection failed)")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail=f"{service} service timeout")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"{service} service error: {str(e)}")


@app.get("/")
def read_root():
    return {"message": "API Gateway is running", "available_services": list(SERVICES.keys())}

class StudentCreate(BaseModel):
    name: str
    age: int
    email: str
    course: str


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    email: Optional[str] = None
    course: Optional[str] = None

@app.get("/gateway/students", dependencies=[Depends(verify_token)])
async def get_all_students():
    return await forward_request("student", "/api/students", "GET")


@app.get("/gateway/students/{student_id}", dependencies=[Depends(verify_token)])
async def get_student(student_id: int):
    return await forward_request("student", f"/api/students/{student_id}", "GET")


@app.post("/gateway/students", dependencies=[Depends(verify_token)])
async def create_student(student: StudentCreate):
    return await forward_request("student", "/api/students", "POST", json=student.model_dump())


@app.put("/gateway/students/{student_id}", dependencies=[Depends(verify_token)])
async def update_student(student_id: int, student: StudentUpdate):
    return await forward_request(
        "student",
        f"/api/students/{student_id}",
        "PUT",
        json=student.model_dump(exclude_none=True),
    )


@app.delete("/gateway/students/{student_id}", dependencies=[Depends(verify_token)])
async def delete_student(student_id: int):
    return await forward_request("student", f"/api/students/{student_id}", "DELETE")

class CourseCreate(BaseModel):
    title: str
    code: str
    credits: int


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    code: Optional[str] = None
    credits: Optional[int] = None

@app.get("/gateway/courses", dependencies=[Depends(verify_token)])
async def get_all_courses():
    return await forward_request("course", "/api/courses", "GET")


@app.get("/gateway/courses/{course_id}", dependencies=[Depends(verify_token)])
async def get_course(course_id: int):
    return await forward_request("course", f"/api/courses/{course_id}", "GET")


@app.post("/gateway/courses", dependencies=[Depends(verify_token)])
async def create_course(course: CourseCreate):
    return await forward_request("course", "/api/courses", "POST", json=course.model_dump())


@app.put("/gateway/courses/{course_id}", dependencies=[Depends(verify_token)])
async def update_course(course_id: int, course: CourseUpdate):
    return await forward_request(
        "course",
        f"/api/courses/{course_id}",
        "PUT",
        json=course.model_dump(exclude_none=True),
    )


@app.delete("/gateway/courses/{course_id}", dependencies=[Depends(verify_token)])
async def delete_course(course_id: int):
    return await forward_request("course", f"/api/courses/{course_id}", "DELETE")