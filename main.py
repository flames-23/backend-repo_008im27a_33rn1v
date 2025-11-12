import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

app = FastAPI(title="AIO Technical Solutions API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Helpers
# -----------------------------

def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    # Convert nested ObjectIds if any
    for k, v in list(doc.items()):
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc

# -----------------------------
# Health
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# -----------------------------
# News API
# -----------------------------
class NewsCreate(BaseModel):
    title_en: str
    title_ar: str
    body_en: Optional[str] = None
    body_ar: Optional[str] = None
    image_url: Optional[str] = None
    tag: Optional[str] = None
    featured: bool = False

@app.get("/api/news")
def list_news(limit: int = 12, featured: Optional[bool] = None):
    try:
        from database import get_documents
        filter_dict = {}
        if featured is not None:
            filter_dict["featured"] = featured
        items = get_documents("newsitem", filter_dict, limit)
        return [serialize_doc(i) for i in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/news/featured")
def featured_news(limit: int = 6):
    return list_news(limit=limit, featured=True)

@app.get("/api/news/{news_id}")
def get_news_item(news_id: str):
    try:
        from database import db
        item = db.newsitem.find_one({"_id": ObjectId(news_id)})
        if not item:
            raise HTTPException(status_code=404, detail="News item not found")
        return serialize_doc(item)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/news")
def create_news(item: NewsCreate):
    try:
        from database import create_document
        new_id = create_document("newsitem", item.model_dump())
        return {"id": new_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/news/seed")
def seed_news():
    """Seed a few demo news items for showcase"""
    try:
        samples = [
            {
                "title_en": "AIO launches next-gen automation suite",
                "title_ar": "إطلاق حزمة الأتمتة من الجيل التالي من AIO",
                "body_en": "We introduced new AI agents that cut process time by 60%.",
                "body_ar": "قدمنا وكلاء ذكاء اصطناعي جدد يقلّصون زمن العمليات بنسبة 60٪.",
                "tag": "Product",
                "featured": True,
                "image_url": "https://images.unsplash.com/photo-1555949963-aa79dcee981d?q=80&w=1400&auto=format&fit=crop"
            },
            {
                "title_en": "AIO partners with leading cloud provider",
                "title_ar": "شراكة AIO مع مزود سحابي رائد",
                "body_en": "This strategic partnership accelerates deployments across MENA.",
                "body_ar": "هذه الشراكة الإستراتيجية تسرّع عمليات النشر في منطقة الشرق الأوسط وشمال أفريقيا.",
                "tag": "Press",
                "featured": False,
                "image_url": "https://images.unsplash.com/photo-1518779578993-ec3579fee39f?q=80&w=1400&auto=format&fit=crop"
            },
            {
                "title_en": "ISO 27001 certification achieved",
                "title_ar": "الحصول على شهادة ISO 27001",
                "body_en": "Security remains our top priority as we scale.",
                "body_ar": "لا تزال الحماية أولويتنا القصوى مع توسعنا.",
                "tag": "Security",
                "featured": True,
                "image_url": "https://images.unsplash.com/photo-1556741533-f6acd6477f8e?q=80&w=1400&auto=format&fit=crop"
            },
        ]
        from database import create_document
        ids: List[str] = []
        for s in samples:
            ids.append(create_document("newsitem", s))
        return {"inserted": len(ids), "ids": ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
