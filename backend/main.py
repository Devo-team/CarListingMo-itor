from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import aiohttp
from bs4 import BeautifulSoup
import hashlib
from datetime import datetime
import asyncio
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage temporaire (remplacer par MongoDB en production)
listings_db = []
filters_db = []

class CarListing(BaseModel):
    id: str
    source: str
    title: str
    price: Optional[float]
    currency: str = "TND"
    location: str
    year: Optional[int]
    imageUrl: Optional[str]
    listingUrl: str
    publishedDate: str
    isNew: bool = False

class UserFilter(BaseModel):
    userId: str
    phone: str
    brands: List[str] = []
    priceMax: Optional[float]
    locations: List[str] = []
    notifySMS: bool = True

async def scrape_tayara():
    listings = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.tayara.tn/ads/c/V%C3%A9hicules",
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=30
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parser les annonces
                    for item in soup.find_all('div', limit=20):
                        try:
                            title = item.get_text(strip=True)[:100]
                            if len(title) > 10:  # Filtre basique
                                listing = CarListing(
                                    id=hashlib.md5(title.encode()).hexdigest()[:16],
                                    source="Tayara",
                                    title=title,
                                    price=None,
                                    location="Tunis",
                                    year=None,
                                    imageUrl=None,
                                    listingUrl="https://www.tayara.tn",
                                    publishedDate=datetime.now().isoformat(),
                                    isNew=True
                                )
                                listings.append(listing)
                        except:
                            continue
    except Exception as e:
        print(f"Erreur Tayara: {e}")
    
    return listings

@app.get("/")
def root():
    return {"status": "Car Monitor API Running", "version": "2.0"}

@app.get("/api/listings")
async def get_listings(limit: int = 50):
    return {
        "success": True,
        "data": listings_db[:limit],
        "count": len(listings_db)
    }

@app.post("/api/scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(scrape_and_save)
    return {"success": True, "message": "Scraping started"}

async def scrape_and_save():
    global listings_db
    new_listings = await scrape_tayara()
    
    # Ajouter les nouvelles
    for listing in new_listings:
        if listing.id not in [l.id for l in listings_db]:
            listings_db.append(listing)
            
            # Envoyer SMS aux utilisateurs
            for user_filter in filters_db:
                if user_filter.notifySMS:
                    await send_sms(user_filter.phone, listing)
    
    # Garder seulement les 100 dernières
    listings_db = listings_db[-100:]

async def send_sms(phone: str, listing: CarListing):
    # TODO: Implémenter Twilio
    print(f"SMS à {phone}: {listing.title}")

@app.post("/api/filters")
async def save_filter(filter_data: UserFilter):
    global filters_db
    filters_db = [f for f in filters_db if f.userId != filter_data.userId]
    filters_db.append(filter_data)
    return {"success": True}

@app.get("/api/filters/{userId}")
async def get_filter(userId: str):
    for f in filters_db:
        if f.userId == userId:
            return {"success": True, "data": f}
    return {"success": False, "data": None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
