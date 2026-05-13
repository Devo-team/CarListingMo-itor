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
import re

app = FastAPI(title="Car Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE = os.getenv("TWILIO_PHONE", "")

# Stockage temporaire (en production, utilisez MongoDB)
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
    priceMax: Optional[float] = None
    locations: List[str] = []
    notifySMS: bool = True

# SCRAPING RÉEL
async def scrape_tayara():
    """Scrape Tayara.tn"""
    listings = []
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            url = "https://www.tayara.tn/ads/c/V%C3%A9hicules"
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Chercher les annonces
                    # Structure à adapter selon le site réel
                    items = soup.find_all(['article', 'div'], class_=re.compile('listing|item|card|ad'), limit=30)
                    
                    for item in items:
                        try:
                            # Extraire le titre
                            title_elem = item.find(['h2', 'h3', 'h4', 'a'])
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            if len(title) < 10:
                                continue
                            
                            # Extraire le prix
                            price_elem = item.find(string=re.compile(r'\d+.*(?:TND|DT|DH)', re.I))
                            price = None
                            if price_elem:
                                price_match = re.search(r'(\d+[\s,]*\d*)', str(price_elem))
                                if price_match:
                                    price_str = price_match.group(1).replace(' ', '').replace(',', '')
                                    try:
                                        price = float(price_str)
                                    except:
                                        pass
                            
                            # Extraire la localisation
                            location = "Tunis"
                            location_elem = item.find(string=re.compile(r'Tunis|Ariana|Sfax|Sousse|Nabeul', re.I))
                            if location_elem:
                                location = location_elem.strip()
                            
                            # Extraire l'URL
                            link = item.find('a', href=True)
                            url = ""
                            if link:
                                url = link['href']
                                if not url.startswith('http'):
                                    url = f"https://www.tayara.tn{url}"
                            
                            # Extraire l'image
                            img = item.find('img', src=True)
                            img_url = None
                            if img:
                                img_url = img['src']
                                if img_url and not img_url.startswith('http'):
                                    img_url = f"https://www.tayara.tn{img_url}"
                            
                            # Extraire l'année
                            year = None
                            year_match = re.search(r'20\d{2}|19\d{2}', title)
                            if year_match:
                                year = int(year_match.group())
                            
                            # Créer l'ID unique
                            listing_id = hashlib.md5(f"{title}{price}{location}".encode()).hexdigest()[:16]
                            
                            listing = CarListing(
                                id=listing_id,
                                source="Tayara",
                                title=title,
                                price=price,
                                location=location,
                                year=year,
                                imageUrl=img_url,
                                listingUrl=url or "https://www.tayara.tn",
                                publishedDate=datetime.now().isoformat(),
                                isNew=True
                            )
                            
                            listings.append(listing)
                            
                        except Exception as e:
                            print(f"Erreur parsing item: {e}")
                            continue
                            
    except Exception as e:
        print(f"Erreur scraping Tayara: {e}")
    
    return listings

async def scrape_9annas():
    """Scrape 9annas.tn"""
    listings = []
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            url = "https://www.9annas.tn/fr/recherche?category=voiture"
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    items = soup.find_all(['article', 'div'], class_=re.compile('ad|listing|item'), limit=30)
                    
                    for item in items:
                        try:
                            title_elem = item.find(['h2', 'h3', 'h4', 'a'])
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            if len(title) < 10:
                                continue
                            
                            price_elem = item.find(string=re.compile(r'\d+.*(?:TND|DT)', re.I))
                            price = None
                            if price_elem:
                                price_match = re.search(r'(\d+[\s,]*\d*)', str(price_elem))
                                if price_match:
                                    try:
                                        price = float(price_match.group(1).replace(' ', '').replace(',', ''))
                                    except:
                                        pass
                            
                            location = "Tunis"
                            location_elem = item.find(string=re.compile(r'Tunis|Ariana|Sfax', re.I))
                            if location_elem:
                                location = location_elem.strip()
                            
                            link = item.find('a', href=True)
                            url = ""
                            if link:
                                url = link['href']
                                if not url.startswith('http'):
                                    url = f"https://www.9annas.tn{url}"
                            
                            img = item.find('img', src=True)
                            img_url = img['src'] if img else None
                            
                            year_match = re.search(r'20\d{2}', title)
                            year = int(year_match.group()) if year_match else None
                            
                            listing_id = hashlib.md5(f"{title}{price}".encode()).hexdigest()[:16]
                            
                            listing = CarListing(
                                id=listing_id,
                                source="9annas",
                                title=title,
                                price=price,
                                location=location,
                                year=year,
                                imageUrl=img_url,
                                listingUrl=url or "https://www.9annas.tn",
                                publishedDate=datetime.now().isoformat(),
                                isNew=True
                            )
                            
                            listings.append(listing)
                            
                        except Exception as e:
                            print(f"Erreur item 9annas: {e}")
                            continue
                            
    except Exception as e:
        print(f"Erreur scraping 9annas: {e}")
    
    return listings

async def scrape_all_sites():
    """Scrape tous les sites en parallèle"""
    results = await asyncio.gather(
        scrape_tayara(),
        scrape_9annas(),
        return_exceptions=True
    )
    
    all_listings = []
    for result in results:
        if isinstance(result, list):
            all_listings.extend(result)
    
    return all_listings

async def send_sms_twilio(phone: str, message: str):
    """Envoyer SMS via Twilio"""
    try:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print(f"Twilio non configuré - SMS simulé vers {phone}: {message}")
            return
        
        from twilio.rest import Client
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            to=phone,
            from_=TWILIO_PHONE,
            body=message[:160]
        )
        
        print(f"✅ SMS envoyé à {phone}: {message.sid}")
        
    except Exception as e:
        print(f"❌ Erreur envoi SMS: {e}")

# ROUTES API
@app.get("/")
def root():
    return {
        "status": "running",
        "version": "2.0",
        "endpoints": ["/api/listings", "/api/scrape", "/api/filters"]
    }

@app.get("/api/listings")
async def get_listings(limit: int = 50):
    """Récupérer les annonces"""
    return {
        "success": True,
        "data": listings_db[:limit],
        "count": len(listings_db)
    }

@app.post("/api/scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    """Déclencher un scraping manuel"""
    background_tasks.add_task(scrape_and_save)
    return {"success": True, "message": "Scraping démarré"}

async def scrape_and_save():
    """Scraper et sauvegarder"""
    global listings_db
    
    print("🕷️ Début du scraping...")
    new_listings = await scrape_all_sites()
    print(f"📊 {len(new_listings)} annonces trouvées")
    
    # Détecter les nouvelles
    existing_ids = {l.id for l in listings_db}
    truly_new = []
    
    for listing in new_listings:
        if listing.id not in existing_ids:
            truly_new.append(listing)
            listings_db.append(listing)
            
            # Notifier les utilisateurs
            for user_filter in filters_db:
                if should_notify(listing, user_filter):
                    await notify_user(user_filter, listing)
    
    # Garder les 100 dernières
    listings_db = sorted(listings_db, key=lambda x: x.publishedDate, reverse=True)[:100]
    
    print(f"✅ {len(truly_new)} nouvelles annonces ajoutées")
    return len(truly_new)

def should_notify(listing: CarListing, user_filter: UserFilter) -> bool:
    """Vérifier si l'utilisateur doit être notifié"""
    if not user_filter.notifySMS:
        return False
    
    if user_filter.priceMax and listing.price:
        if listing.price > user_filter.priceMax:
            return False
    
    if user_filter.locations:
        if listing.location not in user_filter.locations:
            return False
    
    return True

async def notify_user(user_filter: UserFilter, listing: CarListing):
    """Envoyer notification SMS"""
    message = f"🚗 Nouvelle annonce!\n{listing.title}\n💰 {listing.price or 'N/A'} TND\n📍 {listing.location}"
    
    await send_sms_twilio(user_filter.phone, message)

@app.post("/api/filters")
async def save_filter(filter_data: UserFilter):
    """Sauvegarder les préférences"""
    global filters_db
    
    # Supprimer l'ancien filtre de cet utilisateur
    filters_db = [f for f in filters_db if f.userId != filter_data.userId]
    
    # Ajouter le nouveau
    filters_db.append(filter_data)
    
    return {"success": True, "message": "Filtre enregistré"}

@app.get("/api/filters/{user_id}")
async def get_filter(user_id: str):
    """Récupérer les filtres"""
    for f in filters_db:
        if f.userId == user_id:
            return {"success": True, "data": f}
    
    return {"success": False, "data": None}

# Scraping automatique au démarrage
@app.on_event("startup")
async def startup_event():
    print("🚀 API démarrée")
    asyncio.create_task(periodic_scraping())

async def periodic_scraping():
    """Scraping automatique toutes les 15 minutes"""
    while True:
        try:
            await asyncio.sleep(900)  # 15 minutes
            print("⏰ Scraping périodique...")
            await scrape_and_save()
        except Exception as e:
            print(f"❌ Erreur scraping périodique: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
