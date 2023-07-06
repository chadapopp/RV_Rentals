from flask import redirect, render_template, request, send_from_directory, abort, jsonify, url_for, session, flash, json
from flask_app import app
from flask_app.models import user
from flask_app.models.listing import Listing
from flask_app.models.booking import Booking
from flask_app.models.user import User
import uuid
import os
from datetime import datetime

def get_file_extension(filename):
    _, extension = os.path.splitext(filename)
    return extension.lower()

@app.route("/all_rentals")
def show_all_rentals():
    user_listings = Listing.get_all_listings_with_users()
    return render_template('listings/all_rentals.html', user_listings=user_listings)

@app.route("/create_listing")
def create_listing_page():
    if 'user_id' not in session:
        flash ('You must create an account to list your rental', 'warning')
        return redirect ('/sign_up')
    return render_template("listings/create_listing.html")

@app.route("/create_listing", methods=["POST"])
def create_new_listing():
    title = request.form["title"]
    description = request.form["description"]
    rate = request.form["rate"]
    city = request.form["city"]
    state = request.form["state"]
    availability = request.form["availability"]
    user_id = request.form["user_id"]
    listing_id = request.form["listing_id"]

    add_photos = request.files.getlist('add_photos[]')
    photo_paths = []
    for photo in add_photos:
        extension = get_file_extension(photo.filename)
        unique_filename = uuid.uuid4().hex + extension
        file_path = os.path.join(app.instance_path,"uploads", unique_filename)
        photo.save(file_path)
        photo_paths.append(unique_filename)

    if not title or not description or not rate or not city or not state or not availability:
        error_message = "State Must not be abbreviated"
        return jsonify(error=error_message)
    
    listing_data = {
        'title':  title,
        'description': description,
        'rate': rate,
        'city': city,
        'state': state,
        'availability': availability,
        'add_photos': json.dumps(photo_paths),
        'user_id': user_id,
        'listing_id': listing_id
    }
    Listing.create_listing(listing_data)
    return jsonify( success = True, redirect_path = '/all_rentals')


@app.route('/uploaded_file/<filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.instance_path, "uploads"), filename, as_attachment=False)

@app.route('/view_listing/<int:listing_id>')
def view_listing(listing_id):
    listing = Listing.get_listing_by_id(listing_id)
    photos = Listing.get_photos_for_listing(listing_id)
    user_id = listing.user_id
    user = User.get_by_id(user_id)
    return render_template('/listings/show_listing.html', listing = listing, photos = photos, user = user)

@app.route('/all_rentals/show_images/<int:listing_id>')
def show_listing_images(listing_id):
    listing = Listing.get_listing_by_id(listing_id)
    images = Listing.get_photos_for_listing(listing_id)
    if not listing:
        abort(404)  # Listing not found
    return render_template('listings/show_listing_images.html', listing=listing, images = images)

@app.route('/show_my_listings/<int:user_id>')
def show_users_listings(user_id):
    user_id = session['user_id']
    user = User.get_by_id(user_id)
    listings = Listing.get_user(user_id)
    images = []
    for listing in listings:
        listing_images = Listing.get_photos_for_listing(listing.id)
        images.append(listing_images)
    return render_template('/listings/user_listings.html', listings = listings, user = user, images = images)

@app.route("/edit_listing/<int:listing_id>/photos")
def edit_listing_photos(listing_id):
    listing = Listing.get_listing_by_id(listing_id)
    photos = Listing.get_photos_for_listing(listing_id)
    current_time = datetime.utcnow()
    return render_template('listings/edit_listing_photos.html', listing = listing, photos = photos, current_time = current_time)

@app.route("/edit_listing/<int:listing_id>/photos", methods=["POST"])
def editing_listing_upload_photos(listing_id):
    if 'add_photos[]' not in request.files:
        return ("No file selected", 400)
    
    add_photos = request.files.getlist('add_photos[]')
    if len(add_photos) == 0:
        return ("No file selected", 400)
    
    photo_paths = []
    for photo in add_photos:
        extension = get_file_extension(photo.filename)
        unique_filename = uuid.uuid4().hex + extension
        file_path = os.path.join(app.instance_path,"uploads", unique_filename)
        photo.save(file_path)
        photo_paths.append(unique_filename)

    # Merge the new photos with the old photos
    old_photos = Listing.get_photos_for_listing(listing_id)
    old_photos.extend(photo_paths)
    listing_data = {
        'add_photos': json.dumps(old_photos),
        'listing_id': listing_id
    }
    Listing.update_listing_photos(listing_data)
    return jsonify(images = photo_paths)
    
# create a route to delete selected photos from the edit photos page

@app.route('/edit_listing/<int:listing_id>/delete_photos', methods=['POST'])
def delete_selected_photos(listing_id):
    selected_photos = request.form.getlist('delete_photos[]')
    Listing.delete_photos(listing_id, selected_photos)
    return redirect(f"/edit_listing/{listing_id}/photos")

@app.route('/edit_listing/<int:listing_id>')
def edit_listing_form(listing_id):
    listing = Listing.get_listing_by_id(listing_id)
    images = Listing.get_photos_for_listing(listing_id)
    return render_template('/listings/edit_listing.html', listing = listing, images = images)

@app.route('/edit_listing/<int:listing_id>', methods=['POST'])
def edit_listing(listing_id):
    title = request.form.get('title')
    description = request.form.get('description')
    rate = request.form.get('rate')
    city = request.form.get('city')
    state = request.form.get('state')
    availability = request.form.get('availability')
    add_photos = request.form.get('add_photos')

    listing_data = {
        "title": title,
        "description": description,
        "rate": rate,
        "city": city,
        "state": state,
        "availability": availability,
        "add_photos": add_photos,
        "listing_id": listing_id
    }

    Listing.edit_listing(listing_data)
    user_id = session['user_id']
    return redirect('/show_my_listings/' + str(user_id))


@app.route('/remove_listing/delete/<int:listing_id>')
def remove_listing(listing_id):
    listing = Listing.get_listing_by_id(listing_id)
    if listing.has_bookings(listing_id) == True:
        flash("Cannot delete listing. There are bookings associated with it.")
    else:
        Listing.delete(listing_id)
        flash("Listing Deleted Successfully")
    user_id = session['user_id']
    return redirect('/show_my_listings/' + str(user_id))

@app.route("/search_state")
def show_states_with_listings():
    location = request.args.get('search')
    results = Listing.get_searched_state(location)
    user_listings = results  # Update user_listings with filtered results
    return render_template('listings/search_results.html', results=results, searched_state=location, user_listings=user_listings)

#  show available dates for listing
@app.route('/check_availability/<int:listing_id>')
def show_available_dates(listing_id):
    listing = Listing.get_listing_by_id(listing_id)
    dates = Listing.get_available_dates(listing_id)

    if dates is None:
        dates = []

    # booked_dates = Booking.get_booked_dates(listing_id)

    return render_template('/listings/check_availability.html', listing=listing, dates=dates)


