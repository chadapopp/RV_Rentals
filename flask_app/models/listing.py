from flask_app.config.mysqlconnection import connectToMySQL
from flask import session, flash
from flask_app.models import user
import datetime


import json
import os

class Listing:
    DB = "rv_rentals_schema"
    def __init__(self, listing_dict):
        self.id = listing_dict["id"]
        self.title = listing_dict["title"]
        self.description = listing_dict["description"]
        self.rate = listing_dict["rate"]
        self.city = listing_dict['city']
        self.state = listing_dict['state']
        self.availability = listing_dict["availability"]
        self.add_photos = listing_dict["add_photos"]
        self.created_at = listing_dict["created_at"]
        self.updated_at = listing_dict["updated_at"]
        self.user_id = listing_dict["user_id"]
        self.photo_paths = []

    

    @classmethod
    def create_listing(cls, data):
        user_id = session['user_id']
        data["user_id"] = user_id
        query = "INSERT INTO listings (title, description, rate, city, state, availability, add_photos, user_id) VALUES (%(title)s, %(description)s, %(rate)s, %(city)s,%(state)s, %(availability)s, %(add_photos)s, %(user_id)s)"
        results = connectToMySQL(cls.DB).query_db(query, data)

        return results

    @classmethod
    def show_all_listings(cls):
        query = "SELECT * FROM listings"
        result = connectToMySQL(cls.DB).query_db(query)
        return result
    

    @classmethod
    def get_all_listings_with_users(cls):
        query = "SELECT * FROM listings JOIN users on listings.user_id = users.id"
        results = connectToMySQL(cls.DB).query_db(query)
        all_listings = []
        for row in results:
            users = user.User({
                "id" : row["id"],
                "first_name" : row["first_name"],
                "last_name": row["last_name"],
                "email":row["email"],
                "password":row["password"],
                "created_at":row["created_at"],
                "updated_at":row["updated_at"],
            })
            new_listing = Listing({
                "id":row['id'],
                "title" :row["title"],
                "description" :row["description"],
                "rate" :row["rate"],
                "city" :row["city"],
                "state": row["state"],
                "availability" :row["availability"],
                "add_photos" :json.loads(row["add_photos"]),
                "created_at":row["created_at"],
                "updated_at":row["updated_at"],
                "user_id" : users
            })
            new_listing.photo_paths = cls.get_photos_for_listing(new_listing.id)
            all_listings.append(new_listing)
        return all_listings
    
    @classmethod
    def get_listing_by_id(cls, listing_id):
        query = "SELECT * FROM listings WHERE id = %(listing_id)s"
        data = {'listing_id': listing_id}
        results = connectToMySQL(cls.DB).query_db(query, data)
        if len(results) == 0:
            return None
        return cls(results[0])

    @classmethod
    def get_user(cls, user_id):
        query = "SELECT * FROM listings WHERE user_id = %(user_id)s"
        data = {'user_id': user_id}
        results = connectToMySQL(cls.DB).query_db(query, data)
        all_listings = []
        for row in results:
            listing = Listing({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "rate": row["rate"],
                "city": row["city"],
                "state": row["state"],
                "availability": row["availability"],
                "add_photos": row["add_photos"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "user_id": row["user_id"]
            })
            all_listings.append(listing)
        return all_listings

    @classmethod
    def get_photos_for_listing(cls, listing_id):
        query = "SELECT add_photos FROM listings WHERE id = %s"
        result = connectToMySQL(cls.DB).query_db(query, (listing_id,))
        
        if result and result[0]["add_photos"]:
            photo_paths = json.loads(result[0]["add_photos"])
            return photo_paths
        
        return []

    @classmethod
    def has_bookings(cls, listing_id):
        query = """
            SELECT COUNT(*) AS count
            FROM bookings
            WHERE listing_id = %(listing_id)s
        """
        data = {"listing_id": listing_id}
        result = connectToMySQL(cls.DB).query_db(query, data)
        return result[0]['count'] > 0
    
    @classmethod
    def edit_listing(cls, listing_data):
        query = """UPDATE listings SET title=%(title)s, description = %(description)s, rate=%(rate)s, city = %(city)s, state = %(state)s, availability = %(availability)s WHERE id = %(listing_id)s"""
        return connectToMySQL(cls.DB).query_db(query, listing_data)
    

    @classmethod
    def delete(cls, listing_id):
        query = "DELETE from listings WHERE id = %(id)s"
        result = connectToMySQL(cls.DB).query_db(query, {"id":listing_id})
        return result
    
    @classmethod
    def update_listing_photos(cls, data):
        query = "UPDATE listings SET add_photos = %(add_photos)s WHERE id = %(listing_id)s"
        return connectToMySQL(cls.DB).query_db(query, data)
    
    @classmethod
    def get_states(cls):
        query = "SELECT DISTINCT state FROM listings"
        results = connectToMySQL(cls.DB).query_db(query)
        states = [result['state'] for result in results]
        print(results)
        return states
    
    @classmethod
    def search_state(cls, state):
        query = "SELECT DISTINCT state FROM listings WHERE LOWER(state) LIKE %s"
        state = "%s" + state.lower() + "%s"  # Convert the search term to lowercase and add wildcard characters
        results = connectToMySQL(cls.DB).query_db(query, state)
        states = [result['state'] for result in results]
        return states

    @classmethod
    def get_searched_state(cls, state):
        query = "SELECT * FROM listings WHERE state = %(state)s"
        data = {'state': state}
        results = connectToMySQL(cls.DB).query_db(query, data)
        all_listings = []
        for row in results:
            user_id = row["user_id"]
            user_info = user.User.get_by_id(user_id)  # Fetch user information separately
            listing = Listing({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "rate": row["rate"],
                "city": row["city"],
                "state": row["state"],
                "availability": row["availability"],
                "add_photos" :json.loads(row["add_photos"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "user_id": user_info  # Assign the user information to the user_id attribute
            })
            all_listings.append(listing)
        return all_listings

    #  create a method to delete selected photos from the database 
    @classmethod
    def delete_photos(cls, listing_id, selected_photos):
        if not selected_photos:
            return False  # No photos selected for deletion

        query = "UPDATE listings SET add_photos = JSON_REMOVE(add_photos, JSON_UNQUOTE(JSON_SEARCH(add_photos, 'one', %(add_photo)s))) WHERE id = %(listing_id)s"
        for photo in selected_photos:
            data = {'add_photo': photo, 'listing_id': listing_id}
            connectToMySQL(cls.DB).query_db(query, data)
        return True  # Indicate successful deletion

    # get available dates for each listing from the booking class

    @classmethod
    def get_available_dates(cls, listing_id, display_days=365):
        query = """
            SELECT check_in, check_out
            FROM bookings
            WHERE listing_id = %(listing_id)s
        """
        data = {'listing_id': listing_id}
        results = connectToMySQL(cls.DB).query_db(query, data)
        booked_dates = []

        for row in results:
            check_in = row['check_in'].date()
            check_out = row['check_out'].date()
            booked_dates.append((check_in, check_out))

        listing = Listing.get_listing_by_id(listing_id)
        availability = listing.availability.date()

        min_date = max(datetime.date.today(), availability)
        max_date = min_date + datetime.timedelta(days=display_days)

        current_date = min_date
        dates = []

        while current_date <= max_date:
            is_booked = any(
                check_in <= current_date <= check_out for check_in, check_out in booked_dates
            )

            if is_booked:
                dates.append({
                    'title': 'Booked',
                    'start': current_date.isoformat(),
                    'end': (current_date + datetime.timedelta(days=1)).isoformat(),
                    'backgroundColor': 'red',
                    'borderColor': 'red'
                })
            else:
                dates.append({
                    'title': 'Available',
                    'start': current_date.isoformat(),
                    'end': (current_date + datetime.timedelta(days=1)).isoformat(),
                    'backgroundColor': 'green',
                    'borderColor': 'green'
                })

            current_date += datetime.timedelta(days=1)

        return dates







