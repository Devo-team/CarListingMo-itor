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

# Stockage en mémoire
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

async def scrape_tayara():
    """Scrape Tayara.tn"""
    listings = []
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            url = "https://www.tayara.tn/ads/c/V%C3%A9hicules"
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')  # ← html.parser au lieu de lxml
                    
                    # Chercher tous les éléments qui pourraient être des annonces
                    items = soup.find_all(['article', 'div', 'li'], limit=50)
                    
                    for item in items:
                        try:
                            # Chercher le titre
                            title_elem = item.find(['h2', 'h3', 'h4', 'a', 'span'])
                            if not title_elem:
                                continue
                            
                            title = title_elem.get_text(strip=True)
                            
                            # Filtrer les titres trop courts
                            if len(title) < 15 or 'cookie' in title.lower() or 'menu' in title.lower():
                                continue
                            
                            # Chercher le prix
                            price = None
                            price_text = item.find(string=re.compile(r'\d+.*(?:TND|DT|dt)', re.I))
                            if price_text:
                                price_match = re.search(r'(\d+[\s,\.]*\d*)', str(price_text))
                                if price_match:
                                    price_str = price_match.group(1).replace(' ', '').replace(',', '').replace('.', '')
                                    try:
                                        price = float(price_str)
                                    except:
                                        pass
                            
                            # Chercher la localisation
                            location = "Tunis"
                            location_elem = item.find(string=re.compile(r'Tunis|Ariana|Sfax|Sousse|Nabeul|Ben Arous|Bizerte', re.I))
                            if location_elem:
                                loc_match = re.search(r'(Tunis|Ariana|Sfax|Sousse|Nabeul|Ben Arous|Bizerte)', str(location_elem), re.I)
                                if loc_match:
                                    location = loc_match.group(1)
                            
                            # Chercher le lien
                            link = item.find('a', href=True)
                            url_link = ""
                            if link:
                                url_link = link['href']
                                if url_link and not url_link.startswith('http'):
                                    url_link = f"https://www.tayara.tn{url_link}"
                            
                            # Chercher l'image
                            img = item.find('img', src=True)
                            img_url = None
                            if img:
                                img_url = img.get('src') or img.get('data-src')
                                if img_url and not img_url.startswith('http'):
                                    if img_url.startswith('//'):
                                        img_url = f"https:{img_url}"
                                    else:
                                        img_url = f"https://www.tayara.tn{img_url}"
                            
                            # Extraire l'année
                            year = None
                            year_match = re.search(r'20\d{2}|19\d{2}', title)
                            if year_match:
                                year = int(year_match.group())
                            
                            # Vérifier qu'on a au moins un titre et un prix
                            if not title or not price:
                                continue
                            
                            # ID unique
                            listing_id = hashlib.md5(f"{title}{price}{location}".encode()).hexdigest()[:16]
                            
                            listing = CarListing(
                                id=listing_id,
                                source="Tayara",
                                title=title,
                                price=price,
                                location=location,
                                year=year,
                                imageUrl=img_url,
                                listingUrl=url_link or "https://www.tayara.tn",
                                publishedDate=datetime.now().isoformat(),
                                isNew=True
                            )
                            
                            listings.append(listing)
                            
                        except Exception as e:
                            continue
                    
                    print(f"✅ Tayara: {len(listings)} annonces trouvées")
                            
    except Exception as e:
        print(f"❌ Erreur scraping Tayara: {e}")
    
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
                    soup = BeautifulSoup(html, 'html.parser')  # ← html.parser
                    
                    items = soup.find_all(['article', 'div', 'li'], limit=50)
                    
                    for item in items:
                        try:
                            title_elem = item.find(['h2', 'h3', 'h4', 'a'])
                            if not title_elem:
                                continue
                                
                            title = title_elem.get_text(strip=True)
                            if len(title) < 15:
                                continue
                            
                            price = None
                            price_text = item.find(string=re.compile(r'\d+.*(?:TND|DT)', re.I))
                            if price_text:
                                price_match = re.search(r'(\d+[\s,]*\d*)', str(price_text))
                                if price_match:
                                    try:
                                        price = float(price_match.group(1).replace(' ', '').replace(',', ''))
                                    except:
                                        pass
                            
                            if not price:
                                continue
                            
                            location = "Tunis"
                            location_elem = item.find(string=re.compile(r'Tunis|Ariana|Sfax', re.I))
                            if location_elem:
                                location = location_elem.strip()
                            
                            link = item.find('a', href=True)
                            url_link = ""
                            if link:
                                url_link = link['href']
                                if not url_link.startswith('http'):
                                    url_link = f"https://www.9annas.tn{url_link}"
                            
                            img = item.find('img', src=True)
                            img_url = img.get('src') if img else None
                            
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
                                listingUrl=url_link or "https://www.9annas.tn",
                                publishedDate=datetime.now().isoformat(),
                                isNew=True
                            )
                            
                            listings.append(listing)
                            
                        except:
                            continue
                    
                    print(f"✅ 9annas: {len(listings)} annonces trouvées")
                            
    except Exception as e:
        print(f"❌ Erreur scraping 9annas: {e}")
    
    return listings

async def scrape_all_sites():
    """Scrape tous les sites"""
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
            print(f"📱 SMS simulé vers {phone}: {message}")
            return
        
        from twilio.rest import Client
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message_obj = client.messages.create(
            to=phone,
            from_=TWILIO_PHONE,
            body=message[:160]
        )
        
        print(f"✅ SMS envoyé à {phone}: {message_obj.sid}")
        
    except Exception as e:
        print(f"❌ Erreur SMS: {e}")

@app.get("/")
def root():
    return {
        "status": "running",
        "version": "2.0",
        "listings_count": len(listings_db),
        "filters_count": len(filters_db),
        "endpoints": {
            "listings": "/api/listings",
            "scrape": "/api/scrape",
            "filters": "/api/filters"
        }
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
    """Déclencher un scraping"""
    background_tasks.add_task(scrape_and_save)
    return {"success": True, "message": "Scraping démarré"}

async def scrape_and_save():
    """Scraper et sauvegarder"""
    global listings_db
    
    print("🕷️ Début scraping...")
    new_listings = await scrape_all_sites()
    print(f"📊 {len(new_listings)} annonces scrapées")
    
    existing_ids = {l.id for l in listings_db}
    truly_new = []
    
    for listing in new_listings:
        if listing.id not in existing_ids:
            truly_new.append(listing)
            listings_db.append(listing)
            
            # Notifier
            for user_filter in filters_db:
                if should_notify(listing, user_filter):
                    await notify_user(user_filter, listing)
    
    listings_db = sorted(listings_db, key=lambda x: x.publishedDate, reverse=True)[:100]
    
    print(f"✅ {len(truly_new)} nouvelles annonces")
    return len(truly_new)

def should_notify(listing: CarListing, user_filter: UserFilter) -> bool:
    """Vérifier si notifier"""
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
    """Envoyer SMS"""
    message = f"🚗 {listing.title}\n💰 {listing.price or 'N/A'} TND\n📍 {listing.location}"
    await send_sms_twilio(user_filter.phone, message)

@app.post("/api/filters")
async def save_filter(filter_data: UserFilter):
    """Sauvegarder filtre"""
    global filters_db
    filters_db = [f for f in filters_db if f.userId != filter_data.userId]
    filters_db.append(filter_data)
    return {"success": True}

@app.get("/api/filters/{user_id}")
async def get_filter(user_id: str):
    """Récupérer filtre"""
    for f in filters_db:
        if f.userId == user_id:
            return {"success": True, "data": f}
    return {"success": False, "data": None}

@app.on_event("startup")
async def startup_event():
    print("🚀 API démarrée - Car Monitor")
    asyncio.create_task(periodic_scraping())

async def periodic_scraping():
    """Scraping périodique"""
    await asyncio.sleep(60)  # Attendre 1 minute au démarrage
    
    while True:
        try:
            print("⏰ Scraping automatique...")
            await scrape_and_save()
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        await asyncio.sleep(900)  # 15 minutes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
