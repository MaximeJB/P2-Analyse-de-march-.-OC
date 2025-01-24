import requests
import os
from bs4 import BeautifulSoup
import csv

url = "https://books.toscrape.com/"

def scrape_categories():
    """Récupère uniquement les liens des catégories réelles, en ignorant 'books'"""
    print("Début de la recherche des catégories...")
    all_categories_links = []
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        categories = soup.find("div", class_="side_categories")
        links_categories = categories.find_all("a")
        for categories_title in links_categories[1:]:  # Ignorer le premier lien (books)
            addition_url = url + categories_title["href"]
            all_categories_links.append((categories_title.text.strip(), addition_url))
        print(f"{len(all_categories_links)} catégories trouvées")
    return all_categories_links

def download_image(image_url, book_title, category_name):
    """Télécharge l'image d'un livre"""
    print(f"Tentative de téléchargement de l'image pour : {book_title}")  # Debug
    images_dir = category_name + "/book_images"
    os.makedirs(images_dir, exist_ok=True)

     # Nettoyage manuel des caractères spéciaux
    clean_title = book_title.replace(":", "_").replace("#", "_").replace("/", "_")
    clean_title = clean_title.replace("\\", "_").replace("*", "_").replace("?", "_")
    clean_title = clean_title.replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")
    image_name = clean_title.replace(" ", "_").lower()[:50] + ".jpg"  # Limite à 50 caractères
    image_path = os.path.join(images_dir, image_name)
    response_image = requests.get(image_url)
    if response_image.status_code == 200:
        with open(image_path, "wb") as f:
            f.write(response_image.content)
            print(f"Image téléchargée pour : {book_title}")
    else:
        print(f"Erreur de téléchargement de l'image pour {book_title}. URL : {image_url}")

def scrape_book_infos(url_product):
    """Récupère les informations détaillées d'un livre"""
    print(f"Récupération des informations du livre : {url_product}")
    response = requests.get(url_product)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        try:
            # Extraction des informations de base
            products_infos = soup.find_all("td")
            if not products_infos:
                print(f"Aucune information trouvée pour le livre : {url_product}")
                return None
            
            product_infos_values = [info.text for info in products_infos]
            
            upc = product_infos_values[0]
            prices_including_taxes = product_infos_values[2]
            prices_excluding_taxes = product_infos_values[3]
            number_available = product_infos_values[5].replace("In stock (", "").replace("available)", "")
            product_description = soup.find_all("p")[3].text
            category = soup.find_all("a")[3].text
            
            # Extraction de la note de review
            review_element = soup.find("p", class_="star-rating")
            if not review_element:
                print(f"Aucune note de review trouvée pour le livre : {url_product}")
                return None
            
            review = review_element["class"][1]
            mapping = {"Four": 4, "One": 1, "Two": 2, "Three": 3, "Five": 5}
            review_rating = mapping[review]
            
            # Extraction de l'URL de l'image
            thumbnail_div = soup.find("div", class_="thumbnail")
            if not thumbnail_div:
                print(f"Aucune image trouvée pour le livre : {url_product}")
                return None
            
            image_cover = thumbnail_div.find("img")["src"]
            image_clean = image_cover.lstrip("./")  # Supprime les './' et '../'
            image_url = url + image_clean  # Supprimer "catalogue/"
            print(f"URL de l'image scrapée : {image_url}")  # Log de l'URL de l'image
            
            return {
                "upc": upc,
                "price_incl_tax": prices_including_taxes,
                "price_excl_tax": prices_excluding_taxes,
                "availability": number_available,
                "description": product_description,
                "category": category,
                "review_rating": review_rating,
                "image_url": image_url
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des informations du livre : {url_product}. Erreur : {e}")
            return None
    else:
        print(f"Erreur {response.status_code} : Impossible de récupérer la page du livre.")
        return None

def scrape_pages_book_urls(url, category_name):
    """Scrape tous les livres d'une catégorie"""
    print(f"Exploration de la catégorie : {url}")
    all_books = []
    while url:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            books = soup.find_all('article', class_='product_pod')
            
            print(f"{len(books)} livres trouvés sur cette page")
            
            for book in books: 
                title = book.find('h3').find('a')['title']
                # Correction de l'URL du livre
                book_relative_url = book.find('h3').find('a')['href']
                # Supprimer les '../' et construire l'URL correcte
                book_url = url.rsplit('/', 4)[0] + "/" + book_relative_url.replace('../', '')
                print(f"Traitement du livre : {title}")
                print(f"URL du livre : {book_url}")
                
                #Appelle scrape_book_infos pour générer le dictionnaire qui nous intéresse
                book_info = scrape_book_infos(book_url)
                
                if book_info is None:
                    book_info = {}
                
                #formatage du dictionnaires qui nous interessera dans le csv
                book_data = {
                    "titre": title, 
                    "prix": book.find('p', class_='price_color').text, 
                    "Dispo": book.find('p', class_='instock availability').text.strip(),
                    **book_info  
                }
                
                if book_info and 'image_url' in book_info:
                    download_image(book_info['image_url'], title, category_name)

                else:
                    print(f"Aucune URL d'image trouvée pour : {title}")  # Debug
                
                all_books.append(book_data)
            
            next_page = soup.find('li', class_='next')
            if next_page:
                next_page_url = next_page.find('a')['href']
                base_url = url.rsplit('/', 1)[0]
                url = base_url + '/' + next_page_url
                print("Passage à la page suivante")
            else:
                break
        else:
            print(f"Erreur {response.status_code}: Impossible de récupérer la page.")
            break
    
    
    try: 
        folder = os.mkdir(category_name)
    except FileExistsError:
        print(f"Directory '{category_name}' already exists.")


    # Créer un fichier CSV par catégorie
    csv_filename = f"{category_name.replace('/', '_')}.csv"
    with open(category_name + "/" + csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['titre', 'prix', 'Dispo', 'upc', 'price_incl_tax', 'price_excl_tax', 
                      'availability', 'description', 'category', 'review_rating', 'image_url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for book_data in all_books:
            cleaned_book_data = {key: value.replace("Â", "") if isinstance(value, str) else value for key, value in book_data.items()} 
            writer.writerow(cleaned_book_data)
    
    return all_books
    
    

# Exécution principale
print("Démarrage du scraping")
livres_categories_links = scrape_categories()

all_books = []
for category_name, scraping_category_link in livres_categories_links:
    all_books.extend(scrape_pages_book_urls(scraping_category_link, category_name))

print(f"Scraping terminé. {len(all_books)} livres téléchargés.")