from flask import (Blueprint, render_template, abort, request, redirect,
        current_app, url_for, flash, Markup)
from jinja2 import TemplateNotFound
from subscribie.auth import login_required
from subscribie.models import database, Page
from pathlib import Path
import yaml

module_pages = Blueprint('pages', __name__, template_folder='templates')

@module_pages.route('/pages/index') # Module index page
@module_pages.route('/Add-pages')
@login_required
def get_module_pages_index():
    """Return module_pages index page"""

    return render_template('module_pages_index.html')

@module_pages.route('/add-page')
@login_required
def add_page():
    """Return add page form"""
    return render_template('add_page.html')

@module_pages.route('/delete-pages')
@login_required
def delete_pages_list():
    pages = Page.query.all()
    return render_template('delete_pages_list.html', pages=pages)

@module_pages.route('/delete-page/<path>', methods=['POST', 'GET'])
@login_required
def delete_page_by_path(path):
    """Delete a given page"""
    if "confirm" in request.args:
        confirm = False
        return render_template(
            "delete_pages_list.html",
            path=path,
            confirm=False,
        )
    # Perform template file deletion
    templateFile = path + '.html'
    templateFilePath = Path(str(current_app.config['THEME_PATH']), templateFile)
    try:
        templateFilePath.unlink()
    except FileNotFoundError:
        pass

    # Perform page deletion
    page = Page.query.filter_by(path=path).first()
    database.session.delete(page)
    database.session.commit()

    flash(f'Page "{path}" deleted.')
    return redirect(url_for('views.reload_app') + '?next=' + url_for('pages.delete_pages_list'))

@module_pages.route('/edit-pages')
@login_required
def edit_pages_list():
    pages = Page.query.all()
    return render_template('edit_pages_list.html', pages=pages)

@module_pages.route('/edit-page/<path>', methods=['POST', 'GET'])
@login_required
def edit_page(path):
    """Edit a given page"""
    page = Page.query.filter_by(path=path).first()
    if request.method == 'GET':
        # Get page file contents
        template_file = page.template_file
        with open(Path(str(current_app.config['THEME_PATH']), template_file)) as fh:
            rawPageContent = fh.read()
        return render_template('edit_page.html', rawPageContent=rawPageContent, pageTitle=path)

    elif request.method == 'POST':
        try:
            page_title = request.form['page-title']
            page.title = page_title
        except KeyError:
            return "Error: Page title is required"

        try:
            page_body = request.form['page-body']
        except KeyError:
            return "Error: Page body is required"
        # Generate a valid path for url
        pageName = ''
        for char in page_title:
            if char.isalnum():
                pageName += char

        # Generate a valid html filename
        template_file = pageName + '.html'
        page.template_file = template_file

        # Detect if page name has been changed
        titleChanged = False
        if path != pageName:
            titleChanged = True
            page.path = pageName
            oldTemplateFile = path + '.html'
            # Rename old template file .old
            oldTemplatePath = Path(str(current_app.config['THEME_PATH']), oldTemplateFile)
            oldTemplatePath.replace(Path(str(current_app.config['THEME_PATH']), oldTemplateFile + '.old'))
        # Writeout new template_file to file
        with open(Path(str(current_app.config['THEME_PATH']), template_file), 'w') as fh:
            fh.write(page_body)

        flash(Markup('Page edited. <a href="/{}">{}</a> '.format(pageName, pageName)))

        # Save page to database
        database.session.commit()

        # Graceful reload app to load new page
        return redirect(url_for('views.reload_app') + '?next=' + url_for('pages.edit_pages_list'))



@module_pages.route('/add-page', methods=['POST'])
@login_required
def save_new_page():
    """Save the new page

        Writes out a new file <page-name>.html
        and updates page table with the newly 
        added page.
    """
    try:
        page_title = request.form['page-title']
    except KeyError:
        return "Error: Page title is required"

    try:
        page_body = request.form['page-body']
    except KeyError:
        return "Error: Page body is required"

    # Generate a valid path for url
    pageName = ''
    for char in page_title:
        if char.isalnum():
            pageName += char
    # Generate a valid html filename
    template_file = pageName + '.html'

    # Check page doesnt already exist
    page = Page.query.filter_by(path=pageName).first()
    if page is not None:
        flash(Markup(f'The page <a href="/{pageName}">{pageName}</a> already exists'))
        return redirect(url_for('views.reload_app') + '?next=' + url_for('pages.edit_pages_list'))

    # Add new page
    page = Page()
    page.page_name = pageName
    page.path = pageName
    page.template_file = template_file
    database.session.add(page)
    database.session.commit()

    # Writeout template_file to file
    with open(Path(str(current_app.config['THEME_PATH']), template_file), 'w') as fh:
        fh.write(page_body)

    flash(Markup('Your new page <a href="/{}">{}</a> will be visable after reloading'.format(pageName, pageName)))

    # Graceful reload app to load new page
    return redirect(url_for('views.reload_app') + '?next=' + url_for('pages.edit_pages_list'))
