#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import sys
import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import os
from flask_migrate import Migrate
from sqlalchemy import func
from datetime import datetime
import re
from operator import itemgetter


#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db) # TODO: connect to a local postgresql database

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, nullable=True)
    seeking_description = db.Column(db.String(500))
    genres = db.Column(db.ARRAY(db.String()))
    website = db.Column(db.String(120))

    shows = db.relationship('Show', backref="Venue", lazy=True) # (one-to-many) Venue is the parent

    def __repr__(self):
        return '<Venue {}>'.format(self.name)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))

    shows = db.relationship('Show', backref="Artist", lazy=True) # (one-to-many) Artists is the parent

    def __repr__(self):
        return '<Artist {}>'.format(self.name)


class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)    # Start time required
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)   # Artists/Venue id required (Foreignkeys)


    def __repr__(self):
        return '<Show {}{}>'.format(self.artist_id, self.venue_id)


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # Gather data on Venues and populate data list
  all_areas = Venue.query.with_entities(func.count(Venue.id), Venue.city, Venue.state).group_by(Venue.city, Venue.state).all()
  data = []

  for area in all_areas:
    area_venues = Venue.query.filter_by(state=area.state).filter_by(city=area.city).all()
    venue_data = []
    for venue in area_venues:
       venue_shows = Show.query.filter_by(venue_id=venue.id).all()
       num_upcoming = 0
       for show in venue_shows: # Check for number of shows in each venue, then increase by 1
            if show.start_time > now:
                num_upcoming += 1
       venue_data.append({
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": num_upcoming
       })
    # After all venues are added to the list for a given location, add it to the data dictionary
    data.append({
        "city": area.city,
        "state": area.state,
        "venues": venue_data
     })

  return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '')

  # implement search on venues with partial string search. Ensure it is case-insensitive.
  venues = Venue.query.filter(Venue.name.ilike('%' + search_term + '%')).all()
  venue_data = []
  current_date = datetime.now()

  for venue in venues:
    venue_shows = Show.query.filter_by(venue_id=venue.id).all()
    num_upcoming = 0
    for show in venue_shows:
        if show.start_time > current_date:
            num_upcoming += 1

    venue_data.append({
        "id": venue.id,
        "name": venue.name,
        "num_upcoming_shows": num_upcoming
    })

  response = {
        "count": len(venues),
        "data": venue_data
  }

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>') # shows the venue page with the given venue_id
def show_venue(venue_id):
  # Get all the data from the DB and populate the data dictionary
  venue = Venue.query.get(venue_id)
  print(venue)
  if not venue:
        return redirect(url_for('index')) # redirect back to homepage

  else: # Gather shows and orgnize by past and upcoming
        past_shows = []
        past_shows_count = 0
        upcoming_shows = []
        upcoming_shows_count = 0
        current_date = datetime.now()
        for show in venue.shows:
            if show.start_time > current_date:
                upcoming_shows_count += 1
                upcoming_shows.append({
                    "artist_id": show.artist_id,
                    "artist_name": show.artist.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": format_datetime(str(show.start_time))
                })
            if show.start_time < current_date:
                past_shows_count += 1
                past_shows.append({
                    "artist_id": show.artist_id,
                    "artist_name": show.artist.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": format_datetime(str(show.start_time))
                })

        data = {
            "id": venue_id,
            "name": venue.name,
            "genres": venue.genres,
            "address": venue.address,
            "city": venue.city,
            "state": venue.state,
            "phone": (venue.phone[:3] + '-' + venue.phone[3:6] + '-' + venue.phone[6:]),
            "website": venue.website,
            "facebook_link": venue.facebook_link,
            "seeking_talent": venue.seeking_talent,
            "seeking_description": venue.seeking_description,
            "image_link": venue.image_link,
            "past_shows": past_shows,
            "past_shows_count": past_shows_count,
            "upcoming_shows": upcoming_shows,
            "upcoming_shows_count": upcoming_shows_count
        }

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # insert form data as a new Venue record in the db, instead
  form = VenueForm()
  # modify data to be the data object returned from db insertion

  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data
  address = form.address.data.strip()
  phone = form.phone.data
  image_link = form.image_link.data
  website = form.website.data.strip()
  seeking_talent = True if form.seeking_talent.data == 'Yes' else False
  seeking_description = form.seeking_description.data.strip()
  genres = form.genres.data
  facebook_link = form.facebook_link.data.strip()

  if not form.validate(): # If errors, redirect back to form validation
      flash(form.errors)
      return redirect(url_for('create_venue_submission'))

  else:

      error_in_insert = False

      try: # Import form data into database
          created_venue = Venue(name=name, city=city, state=state, address=address, phone=phone, \
                image_link=image_link, website=website, seeking_talent=seeking_talent, seeking_description=seeking_description, \
                genres=genres, facebook_link=facebook_link)

          venue = Venue(name=name, city=city, state=state, address=address, phone=phone, genres=genres, facebook_link=facebook_link, image_link=image_link, website=website, seeking_talent=seeking_talent, seeking_description=seeking_description)
          db.session.add(created_venue)
          db.session.commit()

      except Exception as e:
          error_in_insert = True
          print(f'Exception "{e}" in create_venue_submission()')
          db.session.rollback()
      finally:
          db.session.close()

      if not error_in_insert: # on successful db insert, flash success
          flash('Venue ' + request.form['name'] + ' was successfully listed!')
          return redirect(url_for('index'))
      else: # on unsuccessful db insert, flash an error instead.
          flash('An error occurred. Venue ' + name + ' could not be listed.')
          print("Error in create_venue_submission()")
          abort(500)


@app.route('/venues/<venue_id>/delete', methods=['GET'])
def delete_venue(venue_id):
  venue = Venue.query.get(venue_id)

  if not venue:
      return redirect(url_for('index'))
  else:
      error_on_delete = False
      venue_name = venue.name

      try:
          db.session.delete(venue)
          db.session.commit()
      except:
          error_on_delete = True
          db.session.rollback()
      finally:
          db.session.close()
      if error_on_delete:
            flash(f'An error occurred deleting venue {venue_name}.')
            print("Error in delete_venue()")
            abort(500)
      else:
            flash(f'Successfully removed venue {venue_name}')
            return redirect(url_for('venues'))
            return jsonify({
                'deleted': True,
                'url': url_for('venues')
            })


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    # TODO: replace with real data returned from querying the database
    artists = Artist.query.order_by(Artist.name).all()  # Sort alphabetically
    data = []

    for artist in artists:
        data.append({
            "id": artist.id,
            "name": artist.name
        })


    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists(): # simliar code to venues/search
  search_term = request.form.get('search_term', '')

  # implement search on artists with partial string search. Ensure it is case-insensitive.
  artists = Artist.query.filter(Artist.name.ilike('%' + search_term + '%')).all()
  list_of_artist = []
  current_date = datetime.now()

  for artist in artists:
    artist_shows = Show.query.filter_by(artist_id=artist.id).all()
    num_upcoming = 0
    for show in artist_shows:
        if show.start_time > current_date:
            num_upcoming += 1

    list_of_artist.append({
        "id": list_of_artist.id,
        "name": list_of_artist.name,
        "num_upcoming_shows": num_upcoming
    })

  response = {
    "count": len(artists),
    "data": list_of_artist
  }

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id

  # Get all the data from the DB and populate the data dictionary
  artist = Artist.query.get(artist_id)

  if not artist:
    return render_template('errors/404.html') # "Theres nothing here" sends to error page
  else: # Gather shows and orgnize by past and upcoming
    past_shows = []
    past_shows_count = 0
    upcoming_shows = []
    upcoming_shows_count = 0
    current_date = datetime.now()
    for show in artist.shows:
        if show.start_time > current_date:
            upcoming_shows_count += 1
            upcoming_shows.append({
                "venue_id": show.venue_id,
                "venue_name": show.venue.name,
                "venue_image_link": show.venue.image_link,
                "start_time": format_datetime(str(show.start_time))
            })
        if show.start_time < current_date:
            past_shows_count += 1
            past_shows.append({
                "venue_id": show.venue_id,
                "venue_name": show.venue.name,
                "venue_image_link": show.venue.image_link,
                "start_time": format_datetime(str(show.start_time))
            })

    data = {
        "id": artist_id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        # Put the dashes back into phone number
        "phone": (artist.phone[:3] + '-' + artist.phone[3:6] + '-' + artist.phone[6:]),
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": past_shows,
        "past_shows_count": past_shows_count,
        "upcoming_shows": upcoming_shows,
        "upcoming_shows_count": upcoming_shows_count
    }

    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  # take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  form = ArtistForm()
  artist = Artist.query.get(artist_id)

  if not artist:
      return render_template('errors/404.html')

  else:
    form = ArtistForm(obj=artist)

  artist = {
        "id": artist_id,
        "name": artist.name,
        "city": artist.city,
        "state": artist.state,
        "phone": (artist.phone[:3] + '-' + artist.phone[3:6] + '-' + artist.phone[6:]),
        "image_link": artist.image_link,
        "website": artist.website,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "genres": artist.genres,
        "facebook_link": artist.facebook_link,

    }


  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes

    form = ArtistForm()

    name = form.name.data.strip()
    city = form.city.data.strip()
    state = form.state.data.strip()
    phone = form.phone.data
    image_link = form.image_link.data.strip()
    website = form.website.data.strip()
    seeking_venue = True if form.seeking_venue.data == 'Yes' else False
    seeking_description = form.seeking_description.data.strip()
    genres = form.genres.data
    facebook_link = form.facebook_link.data.strip()

    # Redirect back to form if errors in form validation
    if not form.validate():
        flash( form.errors )
        return redirect(url_for('edit_artist_submission', artist_id=artist_id))

    else:
        error_in_update = False

        # Insert form data into DB
        try:
            artist = Artist.query.get(artist_id)
            # Update fields
            artist.name = name
            artist.city = city
            artist.state = state
            artist.phone = phone
            artist.image_link = image_link
            artist.website = website
            artist.seeking_venue = seeking_venue
            artist.seeking_description = seeking_description
            artist.genres = genres
            artist.facebook_link = facebook_link

            db.session.commit()
        except Exception as e:
            error_in_update = True
            print(f'Exception "{e}" in edit_artist_submission()')
            db.session.rollback()
        finally:
            db.session.close()
        if not error_in_update:
            flash('Artist ' + request.form['name'] + ' was successfully updated!')
            return redirect(url_for('show_artist', artist_id=artist_id))
        else:
            flash('An error occurred. Artist ' + name + ' could not be updated.')
            print("Error in edit_artist_submission()")
            abort(500)




@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  # Get existing data from database
  venue = Venue.query.get(venue_id)

  if not venue: # redirect home if Url entered incorrectly
      return redirect(url_for('index'))
  else:
      form = VenueForm(obj=venue)
  # TODO: populate form with values from venue with ID <venue_id>
  venue = {
        "id": venue_id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": (venue.phone[:3] + '-' + venue.phone[3:6] + '-' + venue.phone[6:]),
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link
    }

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes

  form = VenueForm()

  name = form.name.data.strip()
  city = form.city.data.strip()
  state = form.state.data
  address = form.address.data.strip()
  phone = form.phone.data
  image_link = form.image_link.data.strip()
  website = form.website.data.strip()
  seeking_talent = True if form.seeking_talent.data == 'Yes' else False
  seeking_description = form.seeking_description.data.strip()
  genres = form.genres.data
  facebook_link = form.facebook_link.data.strip()

  if not form.validate(): # # Redirect back to form if errors in form validation
    flash( form.errors )
    return redirect(url_for('edit_venue_submission', venue_id=venue_id))

  else:
    error_in_update = False

        # Insert form data into DB
    try:
            # First get the existing venue object
        venue = Venue.query.get(venue_id)
        # Update fields
        venue.name = name
        venue.city = city
        venue.state = state
        venue.address = address
        venue.phone = phone
        venue.seeking_talent = seeking_talent
        venue.seeking_description = seeking_description
        venue.genres = genres
        venue.image_link = image_link
        venue.website = website
        venue.facebook_link = facebook_link

        db.session.commit()
    except Exception as e:
        error_in_update = True
        print(f'Exception "{e}" in edit_venue_submission()')
        db.session.rollback()
    finally:
        db.session.close()

    if not error_in_update:
            # on successful db update, flash success
        flash('Venue ' + request.form['name'] + ' was successfully updated!')
        return redirect(url_for('show_venue', venue_id=venue_id))
    else:
        flash('An error occurred. Venue ' + name + ' could not be updated.')
        print("Error in edit_venue_submission()")
        abort(500)


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm()

    name = form.name.data.strip()
    city = form.city.data.strip()
    state = form.state.data
    phone = form.phone.data
    image_link = form.image_link.data.strip()
    website = form.website.data.strip()
    seeking_venue = True if form.seeking_venue.data == 'Yes' else False
    seeking_description = form.seeking_description.data.strip()
    genres = form.genres.data
    facebook_link = form.facebook_link.data.strip()

    # Redirect back to form if errors in form validation
    if not form.validate():
        flash( form.errors )
        return redirect(url_for('create_artist_submission'))

    else:
        error_in_insert = False

        # Insert form data into DB
        try:
            # creates the new artist with all fields
            new_artist = Artist(name=name, city=city, state=state, phone=phone, \
                image_link=image_link, website=website, seeking_venue=seeking_venue, seeking_description=seeking_description, \
                genres=genres,facebook_link=facebook_link)
            db.session.add(new_artist)
            db.session.commit()
        except Exception as e:
            error_in_update = True
            db.session.rollback()
            print(sys.exc_info())
        finally:
            db.session.close()

        if not error_in_insert:
            # on successful db insert, flash success
            flash('Artist ' + request.form['name'] + ' was successfully listed!')
            return render_template('pages/home.html')
        else:
            # TODO: on unsuccessful db insert, flash an error instead.
            # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
            flash('An error occurred. Artist ' + name + ' could not be listed.')
            print("Error in create_artist_submission()")
            abort(500)

@app.route('/artists/<artist_id>/delete', methods=['GET'])
def delete_artist(artist_id):
    # Deletes a artist based on AJAX call from the artist page
    artist = Artist.query.get(artist_id)
    if not artist:
        return redirect(url_for('index'))
    else:
        error_on_delete = False
        # Need to hang on to artist name since will be lost after delete
        artist_name = artist.name
        try:
            db.session.delete(artist)
            db.session.commit()
        except:
            error_on_delete = True
            db.session.rollback()
        finally:
            db.session.close()
        if error_on_delete:
            flash(f'An error occurred deleting artist {artist_name}.')
            print("Error in delete_artist()")
            abort(500)
        else:
            flash(f'Successfully removed artist {artist_name}')
            return redirect(url_for('artists'))
            return jsonify({
                'deleted': True,
                'url': url_for('artists')
            })


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # Displays list of shows at /shows
    data = []
    shows = Show.query.all()

    for show in shows:
        # Reference show.artist, show.venue
        data.append({
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": format_datetime(str(show.start_time))
        })

    return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
    form = ShowForm()

    artist_id = form.artist_id.data.strip()
    venue_id = form.venue_id.data.strip()
    start_time = form.start_time.data

    error_in_insert = False

    try:
        new_show = Show(start_time=start_time, artist_id=artist_id, venue_id=venue_id)
        db.session.add(new_show)
        db.session.commit()

    except:
        error_in_insert = True
        print(f'Exception "{e}" in create_show_submission()')
        db.session.rollback()
    finally:
        db.session.close()

    if error_in_insert:
        # on unsuccessful db insert, flash an error instead.
        flash(f'An error occurred.  Show could not be listed.')
        print("Error in create_show_submission()")
    else:
        # on successful db insert, flash success
        flash('Show was successfully listed!')

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
