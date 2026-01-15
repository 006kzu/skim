from nicegui import ui, run, app
import scholar_api
import database
import topics
import os
import re
import auth
import base64
import io
import time
from PIL import Image

# --- INITIALIZATION ---
database.init_db()
app.add_static_files('/assets', 'assets')

from legal_pages import init_legal_pages
init_legal_pages()

# --- CROPPING DEPENDENCIES ---
ui.add_head_html('<link href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.css" rel="stylesheet">', shared=True)
ui.add_head_html('<script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.js"></script>', shared=True)

# Custom Styles
ui.add_head_html('''
<style>
@keyframes highlight-fade {
  0% { background-color: rgba(254, 243, 199, 1); } 
  100% { background-color: transparent; }
}
.blink-highlight {
  animation: highlight-fade 2s ease-out;
}
</style>
''', shared=True)

# --- ICON LOGIC (SMART CACHE) ---
AVAILABLE_ICONS = set()
if os.path.exists('assets'):
    for f in os.listdir('assets'):
        if f.endswith('.png'):
            AVAILABLE_ICONS.add(f.replace('.png', '').lower())

ICON_ALIASES = {
    "artificial intelligence": "artificial_intelligence",
    "ai": "ai",
    "machine learning": "ai",
    "deep learning": "ai",
}


def get_category_icon(category_name):
    if not category_name:
        return None

    clean = category_name.lower().strip()
    file_friendly = clean.replace(" & ", "_and_").replace(" ", "_")

    # 1. Exact Match
    if file_friendly in AVAILABLE_ICONS:
        return f"/assets/{file_friendly}.png"

    # 2. Alias Match
    if clean in ICON_ALIASES:
        alias = ICON_ALIASES[clean]
        if alias in AVAILABLE_ICONS:
            return f"/assets/{alias}.png"

    # 3. Smart Fuzzy Match
    words = clean.split(' ')
    for word in words:
        if word in AVAILABLE_ICONS:
            return f"/assets/{word}.png"

    return None


def render_smart_icon(category, classes, theme_opacity='opacity-100'):
    icon_path = get_category_icon(category)
    if icon_path:
        ui.image(icon_path).classes(
            f"{classes} object-contain drop-shadow-sm transition-transform duration-500 group-hover:scale-105 {theme_opacity}")
    else:
        # Fallback to logo2.png (Monotone Logo)
        ui.image('assets/logo2.png').classes(
            f"{classes} object-contain drop-shadow-sm transition-transform duration-500 group-hover:scale-105 {theme_opacity}")

# --- HELPER: IMPACT THEME ---


def get_impact_theme(paper):
    """
    Returns a dictionary of Tailwind classes based on the paper's Impact Score.
    Handles Score >= 8 (Black/Chrome) vs Standard (White/Chrome).
    """
    score = 0
    try:
        raw_score = str(paper.get('score', '0'))
        match = re.search(r'\d+', raw_score)
        if match:
            score = int(match.group())
    except:
        score = 0

    is_high_impact = score >= 8

    highlight_hex = '#2dd4bf' if is_high_impact else '#0d9488'

    return {
        'is_high_impact': is_high_impact,
        'card_bg': 'bg-slate-900 border-slate-700' if is_high_impact else 'bg-white border-slate-300',
        'text_title': 'text-slate-200' if is_high_impact else 'text-slate-900',
        'text_body': 'text-slate-400' if is_high_impact else 'text-slate-600',
        'text_meta': 'text-slate-500' if is_high_impact else 'text-slate-400',
        'accent_color': 'text-slate-400' if is_high_impact else 'text-slate-500',
        'badge_color': 'grey',
        'btn_primary': 'unelevated color=slate-700 text-color=white' if is_high_impact else 'unelevated color=slate-800 text-color=white',
        'btn_flat': 'flat color=slate-400' if is_high_impact else 'flat color=grey',
        'icon_opacity': 'opacity-100',
        'highlight_hex': highlight_hex,
        'score_color': 'text-teal-400' if is_high_impact else 'text-teal-600'
    }

# --- HELPER: TITLE HIGHLIGHTER ---


def highlight_title(title, keywords, highlight_hex):
    if not title:
        return "Untitled Paper"
    if not keywords or not isinstance(keywords, list):
        return title

    try:
        clean_keywords = [
            k for k in keywords if k and isinstance(k, str) and len(k) > 2]
        sorted_keywords = sorted(clean_keywords, key=len, reverse=True)

        processed_title = title
        for kw in sorted_keywords:
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            processed_title = pattern.sub(
                f'<span style="color: {highlight_hex}; font-weight: 900;">{kw}</span>', processed_title)

        return processed_title
    except Exception as e:
        print(f"Error highlighting title: {e}")
        return title

# --- UI COMPONENTS ---


def display_arxiv_card(container, paper):
    theme = get_impact_theme(paper)

    with container:
        with ui.card().classes(f"w-full hover:shadow-lg transition-all border {theme['card_bg']}"):
            with ui.row().classes('justify-between w-full items-center'):
                with ui.row().classes('gap-2 items-center'):
                    ui.label('ArXiv Search').classes(
                        f"text-xs font-bold uppercase {theme['accent_color']}")
                
                with ui.row().classes('gap-2 items-center'):
                    ui.label(paper.get('date', '')).classes(
                        f"text-xs {theme['text_meta']}")
                    
                    # Favorite Button
                    is_p_fav = False
                    user = auth.get_current_user()
                    fav_icon = 'favorite_border'
                    fav_color = 'grey'
                    
                    # Check if already favored (requires checking DB which is expensive for search results, 
                    # so maybe we default to unchecked unless we want to do a batch check)
                    # For search results, we'll assume unchecked for now or checking requires querying 
                    # favorites for all results. Let's keep it simple: unchecked default.
                    
                    fav_btn = ui.button(icon=fav_icon).props(f'flat round dense color={fav_color} size=sm')

                    def on_fav_click_arxiv(e, p=paper, b=fav_btn):
                        u = auth.get_current_user()
                        if not u:
                            ui.notify('Please login to save papers.', type='warning')
                            return
                        
                        # 1. Ensure Paper is in DB
                        pid = p.get('id')
                        if not pid:
                            # Save it first
                            pid = database.save_paper(p, 'user_search')
                            p['id'] = pid
                        
                        if not pid:
                             ui.notify('Could not save paper details.', type='negative')
                             return

                        # 2. Toggle Favorite
                        # We need to check state. We can store it on the button object?
                        # Or check DB.
                        is_saved = database.is_favorite(u['id'], pid)
                        if is_saved:
                            database.remove_favorite(u['id'], pid)
                            b.props('icon=favorite_border color=grey')
                            ui.notify('Removed from library.')
                        else:
                            database.save_favorite(u['id'], pid)
                            b.props('icon=favorite color=red')
                            ui.notify('Saved to library!')
                    
                    fav_btn.on('click', on_fav_click_arxiv)

            ui.label(paper['title']).classes(
                f"text-lg font-bold leading-tight mt-2 {theme['text_title']}")
            ui.label(f"Authors: {paper['authors']}").classes(
                f"text-sm mt-1 {theme['text_meta']}")

            with ui.expansion('Read Abstract', icon='description').classes(f"w-full text-sm {theme['text_meta']}"):
                ui.markdown(paper['summary']).classes(theme['text_body'])

            ai_result_area = ui.markdown().classes(
                'text-sm text-slate-800 bg-slate-100 p-4 rounded-lg hidden mt-2 w-full')

            ui.separator().classes('mt-4 mb-2 opacity-30')
            with ui.row().classes('w-full justify-between items-center'):
                if paper.get('link'):
                    ui.button('PDF', icon='open_in_new').props(
                        f'href="{paper["link"]}" target="_blank" {theme["btn_flat"]} dense')

                async def run_ai_skim():
                    skim_btn.props('loading')
                    result = await run.io_bound(scholar_api.analyze_with_ai, paper['title'], paper['summary'])
                    ai_result_area.content = result
                    ai_result_area.classes(remove='hidden')
                    skim_btn.props(remove='loading')

                skim_btn = ui.button('Skim with AI', icon='bolt', on_click=run_ai_skim).props(
                    theme['btn_primary'])
            ai_result_area.move(container)


def display_curated_card(container, paper, on_hover=None, on_leave=None, on_click=None, on_unfavorite=None):
    theme = get_impact_theme(paper)

    with container:
        card = ui.card().classes(
            f"w-full min-h-[320px] border-l-4 shadow-sm hover:shadow-md hover:z-50 transition-all duration-300 cursor-pointer flex flex-col gap-6 group relative overflow-visible {theme['card_bg']}")

        border_color = 'border-slate-400' if theme['is_high_impact'] else 'border-slate-300'
        card.classes(add=border_color)

        if on_click:
            card.on('click', lambda: on_click(paper))

        with card:
            with ui.column().classes('absolute -top-14 right-0 z-50 hidden animate-bounce items-end overflow-visible gap-0') as popup_hint_container:
                ui.label('Hint: Click card to lock in inspector').classes(
                    'bg-slate-800 text-white text-[10px] font-bold px-3 py-2 rounded-lg shadow-xl border border-slate-600 whitespace-nowrap relative z-10')
                ui.icon('arrow_drop_down').classes(
                    'text-slate-800 text-2xl -mt-2.5 mr-6 z-20')

            category = paper.get('category', 'General')

            with ui.row().classes('w-full justify-between items-start no-wrap'):
                with ui.column().classes('items-center gap-1'):
                    render_smart_icon(category, 'w-16 h-16',
                                      theme['icon_opacity'])
                    ui.label(category).classes(
                        f"text-[10px] font-black uppercase tracking-wide text-center leading-tight max-w-[100px] {theme['accent_color']}")

                score_val = paper.get('score')
                score_img_path = None

                if score_val is not None:
                    raw_str = str(score_val)
                    match = re.search(r'\d+', raw_str)
                    if match:
                        clean_score = match.group()
                        potential_path = f"assets/scores/{clean_score}.png"
                        if os.path.exists(potential_path):
                            score_img_path = potential_path

                if score_img_path:
                    ui.image(score_img_path).classes(
                        'w-20 h-20 object-contain opacity-100 drop-shadow-[0_0_10px_rgba(255,255,255,0.4)]'
                    )
                else:
                    final_text = str(
                        score_val) if score_val is not None else '?'
                    ui.label(final_text).classes(
                        f"text-6xl font-black {theme['score_color']}")

            # --- FAVORITE BUTTON (Absolute Top Right) ---
            user = auth.get_current_user()
            fav_icon = 'favorite_border'
            fav_color = 'slate-400'
            
            # Check if this paper is in favorites? 
            # We can check cheaply if the paper object has a flag (passed from library view)
            if paper.get('_is_saved'):
                fav_icon = 'favorite'
                fav_color = 'red-500'

            fav_btn = ui.button(icon=fav_icon).props(f'flat round dense color=None').classes(f'absolute top-2 right-2 z-50 text-{fav_color}')

            # New Comment Notification Badge (Only for saved papers)
            new_comments = paper.get('new_comments_count', 0)
            if new_comments > 0:
                with ui.row().classes('absolute top-0 right-12 z-50 bg-red-500 text-white text-[10px] font-bold px-2 py-1 rounded-b-lg shadow-md items-center gap-1 animate-bounce'):
                    ui.icon('mark_chat_unread').classes('text-xs')
                    ui.label(f"{new_comments} new comments")
            
            def on_fav_click_curated(e):
                u = auth.get_current_user()
                if not u:
                    ui.notify('Please login to save papers.', type='warning')
                    return
                
                pid = paper.get('id')
                if not pid:
                     # Should exist for curated, but safe check
                    pid = database.save_paper(paper, 'curated')
                    paper['id'] = pid
                
                is_saved = database.is_favorite(u['id'], pid)
                if is_saved:
                    database.remove_favorite(u['id'], pid)
                    fav_btn.props('icon=favorite_border')
                    fav_btn.classes(remove='text-red-500', add='text-slate-400')
                    ui.notify('Removed from library.')
                    if on_unfavorite:
                        on_unfavorite(paper)
                else:
                    database.save_favorite(u['id'], pid)
                    fav_btn.props('icon=favorite')
                    fav_btn.classes(remove='text-slate-400', add='text-red-500')
                    ui.notify('Saved to library!')

            fav_btn.on('click.stop', on_fav_click_curated)

            with ui.column().classes('w-full gap-3'):
                title_text = paper.get('title', 'Untitled Paper')
                highlights = paper.get('title_highlights') or []
                processed_title = highlight_title(
                    title_text, highlights, theme['highlight_hex'])

                ui.html(processed_title, sanitize=False).classes(
                    f"text-xl font-black leading-tight w-full {theme['text_title']}")
                ui.label(paper.get('summary', 'No summary')).classes(
                    f"text-sm leading-relaxed line-clamp-6 w-full {theme['text_body']}")

                # Footer Action: Read Source
                url = paper.get('url') or paper.get('link')
                if url:
                     ui.button('Read Source', icon='open_in_new').props(
                        'flat dense no-caps color=slate-400 size=xs').classes('self-start -ml-2 hover:bg-slate-100 rounded opacity-60 hover:opacity-100 transition-opacity').on('click.stop', lambda: ui.navigate.to(url, new_tab=True))

        if on_hover:
            def handle_hover_logic():
                if not app.storage.user.get('has_seen_lock_hint_v2', False):
                    popup_hint_container.classes(remove='hidden')
                    app.storage.user['has_seen_lock_hint_v2'] = True
                    ui.timer(4.0, lambda: popup_hint_container.classes(
                        add='hidden'), once=True)
                if on_hover:
                    on_hover(paper)
            card.on('mouseenter', handle_hover_logic)

        if on_leave:
            card.on('mouseleave', on_leave)


def header(on_topic_click=None, on_home_click=None, on_search=None, current_path=None):
    with ui.header().classes('bg-white text-slate-800 border-b border-slate-200 elevation-0 z-50'):
        with ui.row().classes('w-full items-center justify-between h-20 px-6 no-wrap gap-8'):
            with ui.row().classes('items-center cursor-pointer min-w-max').on('click', on_home_click):
                ui.image('/assets/logo.png').classes('w-10 h-10 mr-3')
                with ui.column().classes('gap-0'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label('Skim').classes(
                            'text-xl font-black tracking-tight text-slate-900')
                        ui.label('v3.4').classes(
                            'bg-slate-200 text-slate-700 text-[10px] px-1.5 py-0.5 rounded font-bold')
                    ui.label('Academic Discussion').classes(
                        'text-[9px] font-bold text-slate-400 tracking-widest uppercase')

            with ui.row().classes('flex-grow justify-center max-w-2xl'):
                search_input = ui.input(
                    placeholder='Search ArXiv (e.g. "Fusion")',
                    autocomplete=topics.ALL_TOPICS
                ).props('outlined rounded-full dense bg-slate-50').classes('w-full shadow-none text-sm transition-all focus-within:shadow-md focus-within:bg-white')
                search_input.props('prepend-inner-icon=search')

                def handle_search():
                    if on_search and search_input.value:
                        on_search(search_input.value)
                search_input.on('keydown.enter', handle_search)

            with ui.row().classes('items-center gap-4 min-w-max'):
                # --- Notification Bell ---
                user = auth.get_current_user()
                if user:
                    # Fetch only recent ones for header
                    notifs = database.get_notifications(user['id'])
                    unread_count = len([n for n in notifs if not n.get('is_read')])
                    
                    with ui.button(icon='notifications').props('flat round dense color=slate-600').classes('relative'):
                        badge = None
                        if unread_count > 0:
                            badge = ui.badge(unread_count, color='red').props('floating rounded align=top')
                        
                        async def mark_seen():
                            if unread_count > 0:
                                await run.io_bound(database.mark_all_notifications_read, user['id'])
                                if badge: badge.set_visibility(False)
                        
                        with ui.menu().classes('bg-white border border-slate-200 shadow-xl rounded-xl w-80 p-0 z-[9999]').props('auto-close fit anchor="bottom right" self="top right" offset=[0, 10]').on('show', mark_seen):
                            with ui.column().classes('w-full gap-0'):
                                 ui.label('Notifications').classes('p-4 font-bold text-slate-700 border-b border-slate-100')
                                 
                                 if not notifs:
                                      ui.label('No notifications').classes('p-4 text-sm text-slate-400 italic')
                                 
                                 with ui.scroll_area().classes('max-h-60 w-full'):
                                     for n in notifs:
                                         actor = n.get('actor') or {}
                                         resource = n.get('resource') or {}
                                         bg_class = 'bg-slate-50' if not n.get('is_read') else 'bg-white'
                                         
                                         with ui.item().classes(f'w-full p-3 border-b border-slate-50 {bg_class} transition-colors'):
                                             with ui.row().classes('items-start gap-3 no-wrap w-full'):
                                                 # Avatar
                                                 ava = actor.get('avatar_url')
                                                 if ava:
                                                     ui.image(ava).classes('w-8 h-8 rounded-full object-cover min-w-[2rem]')
                                                 else:
                                                     ui.icon('account_circle').classes('text-2xl text-slate-300')
                                                 
                                                 with ui.column().classes('gap-0 flex-grow'):
                                                      name = actor.get('username') or 'Someone'
                                                      ui.label(f"{name} replied").classes('text-xs font-bold text-slate-700')
                                                      ui.label(resource.get('content', '')[:50] + '...').classes('text-[10px] text-slate-500 leading-tight break-all')
                hub_btn = ui.button('Research Hub', icon='apps').props('flat no-caps color=slate-800 size=md icon-right=arrow_drop_down').classes(
                    'font-bold tracking-tight bg-slate-100 hover:bg-slate-200 rounded-lg px-3')

                hub_timer = None

                def cancel_hub_timer():
                    nonlocal hub_timer
                    if hub_timer:
                        hub_timer.cancel()
                        hub_timer = None

                def start_hub_timer():
                    nonlocal hub_timer
                    cancel_hub_timer()
                    hub_timer = ui.timer(
                        0.2, lambda: mega_menu.close(), once=True)

                with ui.menu().classes('bg-slate-900 border border-slate-700 shadow-2xl rounded-xl p-8 w-[1000px] max-w-[95vw]') as mega_menu:
                    mega_menu.props('no-parent-event')
                    with ui.row().classes('w-full justify-between items-start no-wrap gap-6'):
                        for hub_name, topic_list in topics.TOPIC_HUBS.items():
                            hub_icon = get_category_icon(hub_name)
                            with ui.column().classes('flex-1 gap-4'):
                                with ui.row().classes('items-center gap-2 mb-1 border-b border-slate-700 pb-2 w-full'):
                                    if hub_icon:
                                        ui.image(hub_icon).classes(
                                            'w-6 h-6')
                                    else:
                                        ui.icon('category').classes(
                                            'text-slate-500 text-lg')
                                    ui.label(hub_name).classes(
                                        'text-xs font-black text-slate-500 uppercase tracking-wider')
                                with ui.column().classes('gap-1 w-full'):
                                    for topic in topic_list:
                                        topic_icon = get_category_icon(topic)
                                        with ui.menu_item(on_click=lambda t=topic: on_topic_click(t)).classes('w-full rounded-md hover:bg-slate-800 transition-all duration-200 p-1 hover:scale-105 origin-left'):
                                            with ui.row().classes('items-center gap-3 no-wrap'):
                                                if topic_icon:
                                                    ui.image(topic_icon).classes(
                                                        'w-5 h-5')
                                                else:
                                                    ui.icon('circle').classes(
                                                        'text-slate-600 text-xs')
                                                ui.label(topic).classes(
                                                    'text-xs font-bold text-slate-300 leading-tight')

                hub_btn.on('mouseenter', lambda: [
                           cancel_hub_timer(), mega_menu.open()])
                hub_btn.on('mouseleave', start_hub_timer)
                mega_menu.on('mouseenter', cancel_hub_timer)
                mega_menu.on('mouseleave', start_hub_timer)

                ui.separator().props('vertical').classes('h-6 mx-2 opacity-30')
                ui.separator().props('vertical').classes('h-6 mx-2 opacity-30')
                # --- AUTH / PROFILE SECTION ---
                user = auth.get_current_user()
                if user:
                    # but DB is most accurate. Let's rely on DB for now since we have it.
                    profile = database.get_profile(user['id']) or {}
                    username_text = profile.get('username')
                    
                    # Force Username Creation if logged in but no username (e.g. fresh Google Auth)
                    if not username_text:
                        with ui.dialog().props('persistent') as username_dialog, ui.card().classes('w-[400px] p-8 items-center text-center'):
                            ui.label('Create a Username').classes('text-2xl font-black mb-2')
                            ui.label('Please choose a username to continue to Skim.').classes('text-slate-500 mb-6')
                            
                            u_input = ui.input('Username').classes('w-full mb-6')
                            
                            async def save_initial_username():
                                if not u_input.value or len(u_input.value) < 3:
                                    ui.notify('Username must be at least 3 characters.', type='negative')
                                    return
                                
                                # Check uniqueness handled by DB constraint usually, but we catch error
                                database.update_profile(user['id'], {'username': u_input.value})
                                # We check if it stuck
                                p_check = database.get_profile(user['id'])
                                if p_check and p_check.get('username') == u_input.value:
                                     ui.notify(f'Welcome, {u_input.value}!', type='positive')
                                     username_dialog.close()
                                     ui.navigate.to(app.storage.user.get('referrer_path', '/'), new_tab=False)
                                else:
                                     ui.notify('Error: Username taken or invalid.', type='negative')

                            ui.button('Continue', on_click=save_initial_username).classes('w-full bg-slate-900 text-white')
                        username_dialog.open()

                    # Check for display text again
                    display_name = username_text or user.get('email', '').split('@')[0]
                    
                    with ui.row().classes('items-center gap-3'):
                        ui.label(display_name).classes('text-sm font-bold text-slate-700 hidden sm:block')
                        
                        # Avatar or Icon
                        avatar = user.get('avatar_url') or user.get('metadata', {}).get('avatar_url')
                        
                        with ui.button().props('flat round p-0').classes('overflow-hidden w-9 h-9 border border-slate-200'):
                             if avatar:
                                 ui.image(avatar).classes('w-full h-full object-cover')
                             else:
                                 ui.icon('account_circle', size='md').classes('text-slate-600')
                             
                             with ui.menu():
                                 ui.menu_item('My Library', lambda: ui.navigate.to('/saved'))
                                 ui.menu_item('Profile', lambda: ui.navigate.to('/profile'))
                                 ui.separator()
                                 ui.menu_item('Logout', auth.logout)
                else:
                    # Guest - Auth Dialog
                    with ui.dialog() as auth_dialog, ui.card().classes('w-[400px] p-6'):
                        with ui.tabs().classes('w-full') as tabs:
                            login_tab = ui.tab('Login')
                            signup_tab = ui.tab('Sign Up')
                        
                        with ui.tab_panels(tabs, value=login_tab).classes('w-full mt-4'):
                            with ui.tab_panel(login_tab):
                                email_input = ui.input('Email').classes('w-full mb-2')
                                pass_input = ui.input('Password', password=True, password_toggle_button=True).classes('w-full mb-4')
                                
                                async def handle_login():
                                    u, err = auth.sign_in_with_email(email_input.value, pass_input.value)
                                    if u:
                                        ui.notify('Welcome back!', type='positive')
                                        auth_dialog.close()
                                        redirect_url = app.storage.user.get('referrer_path', '/')
                                        ui.navigate.to(redirect_url)
                                    else:
                                        ui.notify(f'Login failed: {err}', type='negative')

                                ui.button('Log In', on_click=handle_login).classes('w-full mb-2 bg-slate-900 text-white')
                                ui.separator().classes('my-4')
                                ui.button('Continue with Google', icon='img:/assets/google_logo.png', on_click=auth.login_with_google).props('outline color=slate-600').classes('w-full mb-2')
                                ui.button('Continue with X', icon='img:/assets/x_logo.png', on_click=auth.login_with_twitter).props('outline color=slate-950 text-color=slate-900').classes('w-full')

                            with ui.tab_panel(signup_tab):
                                r_name = ui.input('Full Name').classes('w-full mb-2')
                                r_username = ui.input('Username').classes('w-full mb-2')
                                r_email = ui.input('Email').classes('w-full mb-2')
                                r_pass = ui.input('Password', password=True, password_toggle_button=True).classes('w-full mb-4')

                                async def handle_signup():
                                    u, is_logged_in_or_error = auth.sign_up_with_email(r_email.value, r_pass.value, r_name.value, r_username.value)
                                    
                                    if u:
                                        if is_logged_in_or_error is True:
                                            ui.notify('Account created and logged in!', type='positive')
                                            auth_dialog.close()
                                            redirect_url = app.storage.user.get('referrer_path', '/')
                                            ui.navigate.to(redirect_url)
                                        else:
                                            ui.notify('Account created! Please check email to confirm.', type='positive')
                                            auth_dialog.close()
                                    else:
                                        # If u is None, the second arg is the error message
                                        ui.notify(f'Signup failed: {is_logged_in_or_error}', type='negative')

                                ui.button('Create Account', on_click=handle_signup).classes('w-full bg-slate-900 text-white')

                    def open_auth_dialog():
                        if current_path:
                            app.storage.user['referrer_path'] = current_path
                        auth_dialog.open()
                    
                    ui.button('Log In/Sign Up', on_click=open_auth_dialog).props('unelevated color=slate-900 text-color=white size=md rounded').classes('font-bold tracking-wide px-6')


# --- ROOT DASHBOARD (CAROUSEL + IMPACT GUIDE) ---
@ui.page('/')
def dashboard():
    # Set return path for login - REMOVED to prevent stale redirects
    # app.storage.user['referrer_path'] = '/' (Handled by header button now)

    ui.add_head_html('''
        <style>
            .q-carousel__slide { padding: 0; }
        </style>
    ''')

    recent_papers = []
    if database.supabase:
        try:
            res = database.supabase.table("papers").select(
                "*").order("date_added", desc=True).limit(8).execute()
            recent_papers = res.data
        except Exception as e:
            print(f"Error fetching recent papers: {e}")

    def go_topic(t):
        ui.navigate.to(f'/topic/{t}')

    def go_home():
        ui.navigate.to('/')

    def notify_search(q):
        ui.notify(
            f"Search for '{q}' is available inside Topic pages.", type='info')

    header(on_topic_click=go_topic,
           on_home_click=go_home, on_search=notify_search, current_path='/')

    with ui.column().classes('w-full min-h-[calc(100vh-80px)] items-center justify-start py-16 bg-slate-50 gap-16'):

        with ui.column().classes('w-full items-center justify-center'):
            if not recent_papers:
                ui.icon('inbox', size='64px').classes('text-slate-300 mb-4')
                ui.label("No recent papers found.").classes(
                    'text-slate-400 text-xl font-bold')
            else:
                ui.label('Most Recent').classes(
                    'text-slate-500 font-bold uppercase tracking-widest mb-4')

                with ui.column().classes('w-full items-center gap-6'):
                    carousel = ui.carousel(animated=True, arrows=False, navigation=False).props(
                        'infinite autoplay').classes('w-full max-w-5xl h-[400px] rounded-2xl shadow-2xl bg-white')
                    carousel.on('mouseenter', lambda: carousel.props(
                        remove='autoplay'))
                    carousel.on(
                        'mouseleave', lambda: carousel.props(add='autoplay'))

                    with carousel:
                        for i, paper in enumerate(recent_papers):
                            theme = get_impact_theme(paper)

                            with ui.carousel_slide(name=str(i)).classes(f"flex flex-row h-full no-wrap {theme['card_bg']}"):
                                cat = paper.get('category', 'General')
                                side_bg = 'bg-slate-900' if theme['is_high_impact'] else 'bg-slate-100'

                                with ui.column().classes(f"w-1/3 h-full {side_bg} items-center justify-center border-r border-slate-200/50 p-4"):
                                    render_smart_icon(
                                        cat, 'w-28 h-28 mb-4', theme['icon_opacity'])
                                    ui.label(cat).classes(
                                        f"{theme['accent_color']} font-black text-md uppercase tracking-wider text-center leading-tight")
                                    ui.label(paper.get('date', 'Recent')).classes(
                                        f"{theme['text_meta']} text-[10px] font-bold uppercase mt-1")

                                with ui.column().classes(f"w-2/3 h-full {theme['card_bg']} p-6 justify-evenly"):
                                    ui.label(paper.get('title')).classes(
                                        f"{theme['text_title']} text-xl font-black leading-tight")

                                    summary = paper.get(
                                        'summary', 'No summary available.')
                                    ui.label(summary).classes(
                                        f"{theme['text_body']} text-xs leading-relaxed line-clamp-4")

                                    with ui.row().classes('items-center gap-4'):
                                        ui.button('View Analysis', icon='query_stats',
                                                  on_click=lambda p=paper: go_topic(p.get('topic', 'General'))).props('unelevated dense size=sm color=teal-600')

                                        if paper.get('url'):
                                            ui.button('Read Source', icon='open_in_new',
                                                      on_click=lambda u=paper['url']: ui.navigate.to(u, new_tab=True)).props('flat dense size=sm color=teal-600')

                    with ui.row().classes('items-center gap-4'):
                        ui.button(icon='chevron_left', on_click=carousel.previous).props(
                            'flat round color=slate-400 size=lg')
                        dot_refs = []
                        with ui.row().classes('gap-2 items-center'):
                            for i in range(len(recent_papers)):
                                d = ui.button().props('flat round size=xs').classes(
                                    'bg-slate-300 w-2 h-2 rounded-full transition-all duration-300 min-w-0 min-h-0 p-0 shadow-none hover:bg-slate-800')
                                d.on(
                                    'click', lambda idx=i: carousel.set_value(str(idx)))
                                dot_refs.append(d)
                        ui.button(icon='chevron_right', on_click=carousel.next).props(
                            'flat round color=slate-400 size=lg')

                        def update_dots(e):
                            current_val = str(e.value)
                            for idx, dot in enumerate(dot_refs):
                                if str(idx) == current_val:
                                    dot.classes(add='bg-slate-800 w-8',
                                                remove='bg-slate-300 w-2')
                                else:
                                    dot.classes(add='bg-slate-300 w-2',
                                                remove='bg-slate-800 w-8')

                        carousel.on_value_change(update_dots)
                        ui.timer(0.1, lambda: update_dots(
                            type('obj', (object,), {'value': '0'})), once=True)

        # --- SECTION 2: IMPACT SCORE EXPLANATION ---
        with ui.column().classes('w-full items-center justify-center max-w-5xl px-4'):
            ui.separator().classes('w-24 mb-12 opacity-30')
            ui.label('Understanding the Impact Score').classes(
                'text-slate-800 font-black text-2xl uppercase tracking-wider mb-8')

            with ui.row().classes('w-full justify-center gap-6 items-stretch'):
                with ui.card().classes('flex-1 bg-slate-100 border border-slate-200 shadow-none p-8 items-center text-center rounded-xl flex flex-col'):
                    ui.label(
                        '1 - 5').classes('text-4xl font-black text-slate-300 mb-2')
                    ui.label('ACADEMIC').classes(
                        'text-sm font-bold text-slate-400 uppercase tracking-widest mb-3')
                    ui.label('Incremental progress, internal chatter, or niche theoretical optimizations.').classes(
                        'text-xs text-slate-500 leading-relaxed font-medium mb-4')
                    ui.element('div').classes('flex-grow')
                    with ui.column().classes('w-full items-center justify-center pt-4'):
                        ui.separator().classes('w-12 mb-3 opacity-20')
                        with ui.row().classes('items-center gap-2 text-slate-400'):
                            ui.icon('filter_alt', size='xs')
                            ui.label('Filtered from feed').classes(
                                'text-[10px] uppercase font-bold tracking-widest')
                        ui.label('To save you time.').classes(
                            'text-xs font-serif italic text-slate-500')

                with ui.card().classes('flex-1 bg-white border-t-4 border-t-slate-500 shadow-lg p-8 items-center text-center rounded-xl transform scale-105 z-10'):
                    ui.label(
                        '6 - 7').classes('text-4xl font-black text-slate-600 mb-2')
                    ui.label('IMPACTFUL').classes(
                        'text-sm font-bold text-slate-700 uppercase tracking-widest mb-3')
                    ui.label('Real-world utility. Immediate applications in engineering, medicine, or software.').classes(
                        'text-xs text-slate-600 leading-relaxed font-medium')

                with ui.card().classes('flex-1 bg-slate-900 text-white shadow-xl p-8 items-center text-center rounded-xl border border-slate-700'):
                    ui.label('8 - 10').classes(
                        'text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-teal-200 to-teal-400 mb-2')
                    ui.label('TRANSFORMATIVE').classes(
                        'text-sm font-bold text-teal-200 uppercase tracking-widest mb-3')
                    ui.label('Civilization-level shifts. Discoveries that fundamentally change how we live.').classes(
                        'text-xs text-slate-400 leading-relaxed font-medium')

        # --- SECTION 3: CREATOR / DONATE ---
        with ui.column().classes('w-full items-center justify-center max-w-4xl px-4 pb-20'):
             ui.separator().classes('w-24 mb-12 opacity-30')
             with ui.card().classes('w-full bg-white border border-slate-200 shadow-xl p-10 rounded-2xl'):
                 with ui.row().classes('w-full items-center gap-8 no-wrap'):
                      # Creator Image
                      with ui.column().classes('shrink-0'):
                          ui.image('/assets/zachpfp.jpeg').classes(
                              'w-32 h-32 rounded-full object-cover border-4 border-slate-100 shadow-lg')
                      
                      # Text Content
                      with ui.column().classes('flex-grow gap-2'):
                          ui.label('About the Creator of Skim').classes(
                              'text-xs font-black text-slate-400 uppercase tracking-widest mb-1')
                          ui.label('Zach').classes(
                              'text-3xl font-black text-slate-900 leading-tight')
                          ui.html("I am studying electrical engineering at the University of Texas at Dallas. I created Skim while I was stuck in bed after a motorcycle accident to help encourage more intelligent conversation and <strong>more innovation</strong>.", sanitize=False).classes(
                              'text-slate-600 font-medium leading-relaxed max-w-2xl text-base')
                          
                          with ui.row().classes('w-full items-center gap-4 mt-4 bg-slate-50 p-4 rounded-xl border border-slate-100'):
                              ui.label("If you find Skim useful please consider donating to a broke college kid to help pay for AI api calls and ramen ;)").classes(
                                  'text-slate-500 font-bold text-sm italic')
                              ui.button('Support the Developer', icon='coffee', on_click=lambda: ui.navigate.to('https://ko-fi.com/thomaszrm', new_tab=True)).props(
                                  'unelevated color=slate-900 text-color=white rounded-lg').classes('font-bold')


# --- Comment Helpers ---
def build_comment_tree(comments):
    """
    Organizes a flat list of comments into a tree structure.
    """
    comment_map = {c['id']: c for c in comments}
    roots = []
    for c in comments:
        c['replies'] = []
        
    for c in comments:
        pid = c.get('parent_id')
        if pid and pid in comment_map:
            comment_map[pid]['replies'].append(c)
        else:
            roots.append(c)
    roots.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return roots

def render_comment_tree(nodes, depth=0, user=None, on_reply=None, active_reply_id=None, on_submit_reply=None, cancel_reply=None, highlight_cutoff=None):
    """
    Recursively renders comments.
    """
    from datetime import datetime
    
    for c in nodes:
        prof = c.get('profiles') or {}
        
        # Highlight Logic
        created_str = c.get('created_at', '')
        is_new = False
        if highlight_cutoff and created_str:
            try:
                # naive string comparison works for ISO8601 if timezones match
                # but safer to imply: bigger string = newer date
                if created_str > highlight_cutoff:
                     is_new = True
            except:
                pass
                
        # Container for this comment and its children
        container_classes = f'w-full gap-2 {"ml-8 border-l-2 border-slate-100 pl-4" if depth > 0 else "mb-6"}'
        if is_new:
            container_classes += ' blink-highlight rounded-lg p-2 -ml-2' 
            
        with ui.column().classes(container_classes):
            
            # Comment Header
            with ui.row().classes('items-center gap-2 w-full'):
                # Avatar
                ava = prof.get('avatar_url')
                if ava:
                    ui.image(ava).classes('w-6 h-6 rounded-full object-cover border border-slate-200 shadow-sm shrink-0')
                else:
                    ui.icon('account_circle', size='sm').classes('text-slate-300 shrink-0')
                
                # Name & Date
                name = prof.get('full_name') or prof.get('username') or 'Anonymous'
                ui.label(name).classes('text-xs font-bold text-slate-700')
                
                date_str = c.get('created_at', '')[:10]
                label_cls = 'text-[10px] text-slate-400 font-medium'
                if is_new:
                    label_cls = 'text-[10px] text-amber-600 font-bold'
                ui.label(date_str).classes(label_cls)
                
                if is_new:
                    ui.label('NEW').classes('text-[9px] font-black text-white bg-amber-500 px-1 rounded-sm')
                
                # --- VOTE UI ---
                ui.element('div').classes('flex-grow') # Spacer
                
                # Local State for this comment
                current_vote = c.get('user_vote') or 0
                current_score = c.get('score') or 0
                
                # Create UI Elements
                up_btn = ui.button(icon='arrow_upward').props('flat dense round size=xs')
                score_lbl = ui.label(str(current_score)).classes('text-xs font-bold text-slate-600 min-w-[12px] text-center')
                down_btn = ui.button(icon='arrow_downward').props('flat dense round size=xs')

                # Update function for this specific comment's UI
                def update_vote_ui(vote, score, btn_up, btn_down, lbl):
                    btn_up.props(f'color={"teal-600" if vote == 1 else "slate-300"}')
                    btn_down.props(f'color={"red-400" if vote == -1 else "slate-300"}')
                    lbl.text = str(score)

                # Initialize UI
                update_vote_ui(current_vote, current_score, up_btn, down_btn, score_lbl)

                # Handler using closure to capture this comment's state
                # We need to capture the *current* values of the buttons/labels AND the specific comment object 'c'
                async def handle_vote_click(target_val, comment_obj=c, cid=c['id'], b_up=up_btn, b_down=down_btn, lbl=score_lbl):
                     # Do not use 'nonlocal c', use the captured 'comment_obj'
                     if not user:
                         ui.notify('Please login to vote', type='warning')
                         return

                     # Determine new vote logic
                     # We need to know the *current* state. 
                     # Since we don't restart the render, we rely on the button properties or a closure variable.
                     # Let's trust the database or use a mutable container.
                     # Actually, simplest is to just try the optimistic update based on what we see.
                     
                     # But we don't have the "current" state stored in a live way unless we use `c['user_vote']` and update it.
                     old_vote = comment_obj.get('user_vote') or 0 # Handle None from DB
                     new_vote = target_val if old_vote != target_val else 0
                     
                     # Optimistic UI Update? 
                     # No, let's wait for DB for consistency, or do optimistic if slow.
                     # Let's do DB first.
                     success = await run.io_bound(database.vote_comment, user['id'], cid, new_vote)
                     if success:
                         # Calculate new score locally to avoid full re-fetch
                         # Delta calculation
                         delta = new_vote - old_vote
                         comment_obj['score'] = (comment_obj.get('score') or 0) + delta
                         comment_obj['user_vote'] = new_vote
                         
                         update_vote_ui(new_vote, comment_obj['score'], b_up, b_down, lbl)

                # Bind clicks
                # Fix: Capture the local handle_vote_click instance as a default argument 'h' 
                # to prevent all buttons using the last iteration's function
                up_btn.on('click', lambda h=handle_vote_click: h(1))
                down_btn.on('click', lambda h=handle_vote_click: h(-1))

                # Reply Button
                if user:
                    ui.button(icon='reply', on_click=lambda cid=c['id'], cname=name: on_reply(cid, cname)).props(
                        'flat round dense size=xs color=slate-400').tooltip('Reply')
            
            # Comment Body
            ui.label(c['content']).classes('text-sm text-slate-600 leading-relaxed font-medium break-words whitespace-pre-wrap ml-8')
            
            # Inline Reply Input
            if user and active_reply_id == c['id']:
                with ui.column().classes('ml-8 w-full gap-2 mt-2 p-3 bg-slate-50 rounded-lg border border-slate-200 animate-fade'):
                    reply_input = ui.textarea(placeholder=f'Replying to {prof.get("username") or "Anonymous"}...').props(
                        'rows=2 auto-grow outlined flat class="text-sm bg-white"').classes('w-full')
                    reply_input.run_method('focus')
                    
                    async def submit_inline():
                        if on_submit_reply:
                            await on_submit_reply(c['id'], reply_input.value)
                    
                    reply_input.on('keydown.enter.prevent', submit_inline)
                    
                    with ui.row().classes('w-full justify-end gap-2'):
                        ui.button('Cancel', on_click=cancel_reply).props(
                            'flat dense no-caps color=slate-500').classes('text-xs font-bold')
                        ui.button('Reply', on_click=submit_inline).props(
                            'unelevated dense no-caps color=teal-600 text-color=white').classes('px-3 text-xs font-bold rounded-md')

            # Render Children
            if c.get('replies'):
                render_comment_tree(c['replies'], depth=depth+1, user=user, on_reply=on_reply, active_reply_id=active_reply_id, on_submit_reply=on_submit_reply, cancel_reply=cancel_reply, highlight_cutoff=highlight_cutoff)

def open_comment_modal(paper, user_obj, on_view=None):
    """
    Opens a modal dialog for comments.
    """
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-6xl h-[80vh] p-0 gap-0 no-shadow border-none rounded-xl overflow-hidden'):
        dialog.open()
        
        # Capture previous view time for highlighting logic (before we update it)
        # Use fallback if not saved or never viewed (effectively highlights all recent comments if never viewed)
        prev_last_viewed_at = paper.get('last_viewed_at')
        if not prev_last_viewed_at and paper.get('saved_at'):
             prev_last_viewed_at = paper.get('saved_at')
        
        # Mark as viewed when opening comments
        if user_obj and paper.get('id'):
             # We don't check _is_saved here to save a query, the DB function handles it safely
             database.mark_paper_viewed(user_obj['id'], paper['id'])
             # Optimistic local update so if we go back to menu, badge might be gone (requires re-render usually)
             paper['new_comments_count'] = 0
             

             if on_view:
                 on_view()

        # Header
        with ui.row().classes('w-full items-center justify-between p-4 bg-slate-50 border-b border-slate-200'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('forum', size='sm').classes('text-slate-400')
                ui.label('Conversation').classes('text-sm font-bold text-slate-700 uppercase tracking-widest')
            ui.button(icon='close', on_click=dialog.close).props('flat round dense color=slate-400')
        
        # Body (Split View)
        with ui.row().classes('w-full flex-grow overflow-hidden p-0 gap-0 bg-white'):
            
            # Left Panel: Article Context
            with ui.column().classes('w-1/3 h-full overflow-y-auto p-6 border-r border-slate-100 bg-slate-50 gap-6'):
                
                # Title
                ui.label(paper.get('title', 'Unknown Paper')).classes('text-xl font-black text-slate-800 leading-tight')
                
                # Read Source Button
                url = paper.get('url') or paper.get('link')
                if url:
                    ui.button('Read Source', icon='open_in_new', on_click=lambda: ui.open(url, new_tab=True)).props('unelevated no-caps color=teal-700 w-full')
                
                ui.separator().classes('opacity-50')
                
                # Key Findings
                if paper.get('key_findings'):
                    with ui.column().classes('gap-2'):
                        ui.label('KEY FINDINGS').classes('text-xs font-bold text-slate-400 uppercase tracking-widest')
                        for f in paper.get('key_findings', []):
                            ui.label(f"• {f}").classes('text-sm text-slate-700 leading-snug font-medium')
                            
                # Implications
                if paper.get('implications'):
                    with ui.column().classes('gap-2'):
                        ui.label('IMPLICATIONS').classes('text-xs font-bold text-slate-400 uppercase tracking-widest')
                        imps = paper.get('implications', [])
                        if isinstance(imps, list):
                            for imp in imps:
                                ui.label(f"➔ {imp}").classes('text-sm text-slate-700 leading-snug')
                        else:
                            ui.markdown(str(imps)).classes('text-sm leading-snug')

            # Right Panel: Discussion (Scrollable)
            content_area = ui.column().classes('w-2/3 h-full overflow-y-auto p-6 gap-6')
        
        # State
        reply_ctx = {'id': None}
        active_reply_id = None
        
        async def refresh_list():
            content_area.clear()
            # Pass user_id for vote status
            uid = auth.get_current_user().get('id') if auth.get_current_user() else None
            comments = await run.io_bound(database.get_comments, paper['id'], uid)
            
            with content_area:
                # 1. Main Input (Top)
                user = auth.get_current_user() # Refresh user state
                
                with ui.column().classes('w-full items-stretch gap-2 mb-4'):
                     with ui.row().classes('items-center gap-2 mb-1'):
                        if user:
                            avatar = user.get('avatar_url') or user.get('metadata', {}).get('avatar_url')
                            if avatar:
                                ui.image(avatar).classes('w-6 h-6 rounded-full object-cover border border-slate-200 shadow-sm')
                            else:
                                ui.icon('account_circle', size='sm').classes('text-slate-300')
                            ui.label('Join the conversation').classes('text-xs font-bold text-slate-500 uppercase tracking-widest')
                        else:
                            ui.icon('lock', size='sm').classes('text-slate-300')
                            ui.label('Login to comment').classes('text-xs font-bold text-slate-400 uppercase tracking-widest')
                     
                     if user:
                        c_input = ui.textarea(placeholder='Write a comment...').props(
                            'rows=2 auto-grow outlined flat class="text-sm"').classes('w-full bg-slate-50 rounded-lg')
                        
                        async def submit_main():
                            if not c_input.value or not c_input.value.strip(): return
                            await run.io_bound(database.add_comment, user['id'], paper['id'], c_input.value, None)
                            await refresh_list()
                        
                        c_input.on('keydown.enter.prevent', submit_main)
                        with ui.row().classes('w-full justify-end mt-2'):
                            ui.button('Post', icon='send', on_click=submit_main).props(
                                'unelevated no-caps color=teal-600 text-color=white dense').classes('px-4 rounded-full font-bold')
                     else:
                        ui.textarea(placeholder='Login to share your thoughts').props(
                            'disable rows=2 outlined flat class="text-sm"').classes('w-full opacity-60 bg-slate-50 rounded-lg')
                
                ui.separator().classes('my-4 opacity-30')
                
                # 2. List
                if not comments:
                     ui.label('No comments yet. Be the first!').classes('text-xs text-slate-400 italic pl-2')
                else:
                    roots = build_comment_tree(comments)
                    
                    # Callbacks
                    async def on_reply_click(cid, cname):
                         nonlocal active_reply_id
                         active_reply_id = cid
                         await refresh_list()
                    
                    async def on_cancel_reply():
                         nonlocal active_reply_id
                         active_reply_id = None
                         await refresh_list()
                         
                    async def on_submit_reply(pid, content):
                         if not content or not content.strip(): return
                         nonlocal active_reply_id
                         await run.io_bound(database.add_comment, user['id'], paper['id'], content, pid)
                         active_reply_id = None
                         await refresh_list()
                         
                    render_comment_tree(roots, user=user, on_reply=on_reply_click, active_reply_id=active_reply_id, on_submit_reply=on_submit_reply, cancel_reply=on_cancel_reply, highlight_cutoff=prev_last_viewed_at)

        # Initial Load
        ui.timer(0.1, refresh_list, once=True)


@ui.page('/topic/{topic_name}')
def topic_pages(topic_name: str):
    # Set return path for login - REMOVED
    # app.storage.user['referrer_path'] = f'/topic/{topic_name}'

    ui.add_head_html('''
    <style>
        .q-item__section--avatar { min-width: 50px !important; }
        .q-item__section--avatar .q-icon { font-size: 40px !important; }
        .q-item__section--avatar img { width: 40px !important; height: 40px !important; }
        ::-webkit-scrollbar { height: 0px; background: transparent; }
    </style>
    ''')



    feed_label = None
    feed_grid = None
    pinned_paper = None
    results_grid = None

    i_category = None
    i_icon = None
    i_score = None
    i_title = None
    i_lock_btn = None
    i_findings_container = None
    i_impact_container = None
    i_comments_container = None
    i_authors_label = None
    default_view = None
    info_view = None
    i_read_source_btn = None
    i_comment_btn = None
    i_actions_container = None

    reset_timer = None
    
    # State for scroll reset
    last_paper_id = None
    last_hover_time = 0.0
    i_scroll_area = None

    def go_home():
        ui.navigate.to('/')

    def go_topic(t):
        ui.navigate.to(f'/topic/{t}')

    async def perform_search(query):
        if not query:
            return
        ui.notify(f'Searching ArXiv for "{query}"...')
        if results_grid:
            results_grid.clear()
        if feed_grid:
            feed_grid.clear()
        if feed_label:
            feed_label.text = f'Search Results: "{query}"'
        papers = await run.io_bound(scholar_api.search_arxiv, query)
        if not papers:
            ui.notify('No results found.', type='warning')
        if feed_grid:
            with feed_grid:
                for paper in papers:
                    display_arxiv_card(feed_grid, paper)

    def cancel_reset_timer():
        nonlocal reset_timer
        if reset_timer:
            reset_timer.cancel()
            reset_timer = None

    def start_reset_timer():
        if pinned_paper:
            return
        nonlocal reset_timer
        if reset_timer:
            reset_timer.cancel()
        reset_timer = ui.timer(0.1, hard_reset_inspector, once=True)

    def hard_reset_inspector():
        if pinned_paper:
            return
        if info_view:
            info_view.classes(add='hidden')
        if default_view:
            default_view.classes(remove='hidden')

    def toggle_pin(paper=None):
        nonlocal pinned_paper
        if pinned_paper and (paper is None or pinned_paper == paper):
            pinned_paper = None
            if i_lock_btn:
                i_lock_btn.props('icon=lock_open color=slate-300')
            return
        if paper:
            pinned_paper = paper
            update_inspector(paper, force=True)
            if i_lock_btn:
                i_lock_btn.props('icon=lock color=teal')

    def update_inspector(paper, force=False):
        cancel_reset_timer()
        if pinned_paper and not force:
            return
        if default_view:
            default_view.classes(add='hidden')
        if info_view:
            info_view.classes(remove='hidden')

        # Scroll Reset Logic
        nonlocal last_paper_id, last_hover_time
        current_time = time.time()
        
        # Scenario A: New Paper -> Always Reset
        if paper['id'] != last_paper_id:
            if i_scroll_area:
                i_scroll_area.scroll_to(percent=0.0, duration=0)
            last_paper_id = paper['id']
            last_hover_time = current_time
            
        # Scenario B: Same Paper, but "Long" Absence -> Reset
        elif (current_time - last_hover_time) > 5.0:
            if i_scroll_area:
                i_scroll_area.scroll_to(percent=0.0, duration=0)
            last_hover_time = current_time
        else:
            # Short absence -> maintain scroll, update timestamp
            last_hover_time = current_time

        cat = paper.get('category', 'Unknown')
        if i_category:
            i_category.text = cat
        if i_icon:
            ico = get_category_icon(cat)
            if ico:
                i_icon.set_source(ico)
            else:
                i_icon.set_source('/assets/logo2.png')

        score = paper.get('score', '?')
        if i_score:
            i_score.text = f"{score}/10"
        if i_title:
            # Highlight Logic
            theme = get_impact_theme(paper)
            highlights = paper.get('title_highlights') or []
            processed_title = highlight_title(paper['title'], highlights, theme['highlight_hex'])
            i_title.content = processed_title
        if i_authors_label:
            authors = paper.get('authors', 'Unknown')
            if isinstance(authors, list):
                authors = ", ".join(authors)
            i_authors_label.text = authors
        if i_lock_btn:
            is_pinned = (pinned_paper == paper)
            i_lock_btn.props(
                f'icon={"lock" if is_pinned else "lock_open"} color={"teal" if is_pinned else "slate-300"}')
        if i_findings_container:
            i_findings_container.clear()
            with i_findings_container:
                for f in paper.get('key_findings', []):
                    ui.label(f"• {f}").classes(
                        'text-sm text-slate-700 leading-snug font-medium')
        if i_impact_container:
            i_impact_container.clear()
            with i_impact_container:
                imps = paper.get('implications', [])
                if isinstance(imps, list):
                    for imp in imps:
                        ui.label(f"➔ {imp}").classes(
                            'text-sm text-slate-800 leading-snug')
                else:
                    ui.markdown(str(imps)).classes('text-sm leading-snug')

        if i_actions_container:
            i_actions_container.clear()
            with i_actions_container:
                 # Comment Button
                 user = auth.get_current_user()
                 # Use icon-only button, green (teal-600)
                 ui.button(icon='forum', on_click=lambda: open_comment_modal(paper, user)) \
                    .props('flat round color=teal-600').tooltip('Join Conversation')
                 
                 # Read Source Button
                 url = paper.get('url') or paper.get('link')
                 if url:
                     ui.button('Read Source', icon='open_in_new') \
                        .props(f'flat dense color=teal-700 size=sm href="{url}" target="_blank"')

                    





                


                            
 










    def render_feed(papers, title):
        if feed_label:
            feed_label.set_text(title)
        if feed_grid:
            feed_grid.clear()
        if not papers and feed_grid:
            with feed_grid:
                with ui.column().classes('w-full col-span-2 items-center py-12 text-slate-400'):
                    ui.icon('inbox', size='48px').classes('mb-4')
                    ui.label('No papers found yet.').classes('text-lg')
            return
        if feed_grid:
            with feed_grid:
                for paper in papers:
                    display_curated_card(feed_grid, paper, on_hover=update_inspector,
                                         on_leave=lambda: start_reset_timer(), on_click=toggle_pin)

    def load_topic_feed(topic):
        nonlocal pinned_paper
        pinned_paper = None
        hard_reset_inspector()
        papers = database.get_papers_by_topic(topic)
        papers.sort(key=lambda x: str(
            x.get('date') or '0000-00-00'), reverse=True)
        render_feed(papers, f'Topic: {topic}')

    header(on_topic_click=go_topic, on_home_click=go_home,
           on_search=perform_search, current_path=f'/topic/{topic_name}')

    drawer = ui.right_drawer(value=True).props('width=450').classes(
        'bg-slate-50 border-l border-slate-200 p-6 column no-wrap gap-4')
    drawer.on('mouseenter', cancel_reset_timer)
    drawer.on('mouseleave', lambda: start_reset_timer())

    with drawer:
        with ui.row().classes('w-full items-center justify-between'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('manage_search').classes('text-base text-slate-400')
                ui.label('Inspector').classes(
                    'text-sm font-bold text-slate-400 uppercase tracking-wider')
            
            i_lock_btn = ui.button(icon='lock_open').props(
                'flat round dense color=slate-300').on('click', lambda: toggle_pin(None))
            ui.tooltip('Click card to Pin/Unpin').classes('bg-slate-800 text-white')

        with ui.column().classes('w-full flex-grow relative transition-all overflow-hidden'):
            with ui.column().classes('w-full h-full items-center justify-center text-center') as default_view:
                ui.image(
                    '/assets/logo2.png').classes('w-32 h-32 mb-4')
                ui.label('Cards you lock will appear here').classes(
                    'text-lg font-bold text-slate-400')

            with ui.column().classes('hidden w-full flex-grow bg-white rounded-xl border border-slate-200 shadow-md animate-fade overflow-hidden') as info_view:
                with ui.row().classes('w-full justify-between items-center p-6 border-b border-slate-100 bg-slate-50'):
                    with ui.row().classes('items-center gap-3'):
                        i_icon = ui.image().classes('w-16 h-16')
                        i_category = ui.label('Category').classes(
                            'text-xs font-bold text-teal-600 uppercase tracking-wide')
                    with ui.row().classes('items-center gap-2'):
                        i_score = ui.badge(
                            '0/10', color='teal').props('outline size=md')

                with ui.scroll_area().classes('w-full p-6 flex-grow') as i_scroll_area:
                    i_title = ui.html('Paper Title', sanitize=False).classes(
                        'text-lg font-black text-slate-800 leading-snug mb-2')
                    
                    # Read Source Button
                    i_read_source_btn = ui.button('Read Source', icon='open_in_new').props(
                         'flat dense color=teal-700 size=sm').classes('hidden mb-6 self-start -ml-2')
                    ui.label('CORE FINDINGS').classes(
                        'text-xs font-bold text-slate-400 uppercase mb-2 tracking-wider')
                    i_findings_container = ui.column().classes('w-full gap-3 mb-6')
                    ui.separator().classes('mb-6 opacity-50')
                    ui.label('IMPLICATIONS').classes(
                        'text-xs font-bold text-slate-400 uppercase mb-2 tracking-wider')
                    i_impact_container = ui.column().classes('w-full gap-3')
                    
                    
                with ui.row().classes('w-full p-4 bg-slate-50 border-t border-slate-100 mt-auto justify-between items-center'):
                    with ui.column().classes('gap-0'):
                        ui.label('AUTHORS').classes(
                            'text-[10px] font-bold text-slate-400 tracking-wider mb-1')
                        i_authors_label = ui.label('Loading...').classes(
                            'text-xs text-slate-600 italic leading-tight')
                    
                    with ui.row().classes('items-center gap-2') as i_actions_container:
                        pass

    with ui.column().classes('w-full min-h-[calc(100vh-80px)] bg-slate-50 p-6 gap-8'):
        results_grid = ui.grid(columns=1).classes('w-full gap-4 hidden')
        with ui.row().classes('w-full items-center justify-between mb-4'):
            feed_label = ui.label('Loading...').classes(
                'text-2xl font-bold text-slate-800')
            # REMOVED RESET BUTTON
        feed_grid = ui.grid(columns=2).classes('w-full gap-4')

    ui.timer(0.1, lambda: load_topic_feed(topic_name), once=True)



# --- AUTH & PROFILE PAGES ---

@ui.page('/auth/callback')
def auth_callback(code: str = ''):
    """Handles the OAuth callback."""
    if code:
        success = auth.handle_auth_callback(code)
        if success:
            ui.notify('Login successful!', type='positive')
            # Redirect back to where they started
            redirect_url = app.storage.user.get('referrer_path', '/')
            ui.navigate.to(redirect_url) 
        else:
            ui.notify('Login failed.', type='negative')
            ui.navigate.to('/')
    else:
        ui.navigate.to('/')

@ui.page('/saved')
def saved_papers_page():
    # app.storage.user['referrer_path'] = '/saved' - REMOVED
    header(on_topic_click=lambda t: ui.navigate.to(f'/topic/{t}'), 
           on_home_click=lambda: ui.navigate.to('/'), current_path='/saved')
    
    user = auth.get_current_user()
    if not user:
        ui.label('Please login to view your library.').classes('m-8 text-lg')
        return

    # --- INSPECTOR LOGIC (Copied & Adapted from topic_pages) ---
    pinned_paper = None
    reset_timer = None

    i_category = None
    i_icon = None
    i_score = None
    i_title = None
    i_lock_btn = None
    i_findings_container = None
    i_impact_container = None
    i_comments_container = None
    
    # State for scroll reset
    last_paper_id = None
    last_hover_time = 0.0
    i_scroll_area = None

    i_authors_label = None
    default_view = None
    info_view = None
    i_read_source_btn = None
    i_actions_container = None

    def cancel_reset_timer():
        nonlocal reset_timer
        if reset_timer:
            reset_timer.cancel()
            reset_timer = None

    def start_reset_timer():
        if pinned_paper:
            return
        nonlocal reset_timer
        if reset_timer:
            reset_timer.cancel()
        reset_timer = ui.timer(0.1, hard_reset_inspector, once=True)

    def hard_reset_inspector():
        if pinned_paper:
            return
        if info_view:
            info_view.classes(add='hidden')
        if default_view:
            default_view.classes(remove='hidden')

    def toggle_pin(paper=None):
        nonlocal pinned_paper
        if pinned_paper and (paper is None or pinned_paper == paper):
            pinned_paper = None
            if i_lock_btn:
                i_lock_btn.props('icon=lock_open color=slate-300')
            return
        if paper:
            pinned_paper = paper
            update_inspector(paper, force=True)
            if i_lock_btn:
                i_lock_btn.props('icon=lock color=teal')

    def update_inspector(paper, force=False):
        cancel_reset_timer()
        if pinned_paper and not force:
            return
        if default_view:
            default_view.classes(add='hidden')
        if info_view:
            info_view.classes(remove='hidden')

        # Scroll Reset Logic
        nonlocal last_paper_id, last_hover_time
        current_time = time.time()
        
        # Scenario A: New Paper -> Always Reset
        if paper['id'] != last_paper_id:
            if i_scroll_area:
                i_scroll_area.scroll_to(percent=0.0, duration=0)
            last_paper_id = paper['id']
            last_hover_time = current_time
            
        # Scenario B: Same Paper, but "Long" Absence -> Reset
        elif (current_time - last_hover_time) > 5.0:
            if i_scroll_area:
                i_scroll_area.scroll_to(percent=0.0, duration=0)
            last_hover_time = current_time
        else:
            # Short absence -> maintain scroll, update timestamp
            last_hover_time = current_time

        cat = paper.get('category', 'Unknown')
        if i_category:
            i_category.text = cat
        if i_icon:
            ico = get_category_icon(cat)
            if ico:
                i_icon.set_source(ico)
            else:
                i_icon.set_source('/assets/logo2.png')

        score = paper.get('score', '?')
        if i_score:
            i_score.text = f"{score}/10"
        if i_title:
            # Highlight Logic
            theme = get_impact_theme(paper)
            highlights = paper.get('title_highlights') or []
            processed_title = highlight_title(paper['title'], highlights, theme['highlight_hex'])
            i_title.content = processed_title
        if i_authors_label:
            authors = paper.get('authors', 'Unknown')
            if isinstance(authors, list):
                authors = ", ".join(authors)
            i_authors_label.text = authors

        if i_lock_btn:
            is_pinned = (pinned_paper == paper)
            i_lock_btn.props(
                f'icon={"lock" if is_pinned else "lock_open"} color={"teal" if is_pinned else "slate-300"}')
        if i_findings_container:
            i_findings_container.clear()
            with i_findings_container:
                for f in paper.get('key_findings', []):
                    ui.label(f"• {f}").classes(
                        'text-sm text-slate-700 leading-snug font-medium')
        if i_impact_container:
            i_impact_container.clear()
            with i_impact_container:
                imps = paper.get('implications', [])
                if isinstance(imps, list):
                    for imp in imps:
                        ui.label(f"➔ {imp}").classes(
                            'text-sm text-slate-800 leading-snug')
                else:
                    ui.markdown(str(imps)).classes('text-sm leading-snug')

        if i_actions_container:
            i_actions_container.clear()
            with i_actions_container:
                 # Comment Button
                 user = auth.get_current_user()
                 # Use icon-only button, green (teal-600)
                 # Pass render_library to refresh UI when comments are viewed
                 ui.button(icon='forum', on_click=lambda: open_comment_modal(paper, user, on_view=render_library)) \
                    .props('flat round color=teal-600').tooltip('Join Conversation')
                 
                 # Read Source Button
                 url = paper.get('url') or paper.get('link')
                 if url:
                     ui.button('Read Source', icon='open_in_new') \
                        .props(f'flat dense color=teal-700 size=sm href="{url}" target="_blank"')
                

                

                
 



    # --- LAYOUT ---
    
    # Right Drawer (Inspector)
    drawer = ui.right_drawer(value=True).props('width=450').classes(
        'bg-slate-50 border-l border-slate-200 p-6 column no-wrap gap-4')
    drawer.on('mouseenter', cancel_reset_timer)
    drawer.on('mouseleave', lambda: start_reset_timer())

    with drawer:
        with ui.row().classes('w-full items-center justify-between'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('manage_search').classes('text-base text-slate-400')
                ui.label('Inspector').classes(
                    'text-sm font-bold text-slate-400 uppercase tracking-wider')

            i_lock_btn = ui.button(icon='lock_open').props(
                'flat round dense color=slate-300').on('click', lambda: toggle_pin(None))
            ui.tooltip('Click card to Pin/Unpin').classes('bg-slate-800 text-white')

        with ui.column().classes('w-full flex-grow relative transition-all overflow-hidden'):
            with ui.column().classes('w-full h-full items-center justify-center text-center') as default_view:
                ui.image(
                    '/assets/logo2.png').classes('w-32 h-32 mb-4')
                ui.label('Hover a card to inspect').classes(
                    'text-lg font-bold text-slate-400')

            with ui.column().classes('hidden w-full flex-grow bg-white rounded-xl border border-slate-200 shadow-md animate-fade overflow-hidden') as info_view:
                with ui.row().classes('w-full justify-between items-center p-6 border-b border-slate-100 bg-slate-50'):
                    with ui.row().classes('items-center gap-3'):
                        i_icon = ui.image().classes('w-16 h-16')
                        i_category = ui.label('Category').classes(
                            'text-xs font-bold text-teal-600 uppercase tracking-wide')
                    with ui.row().classes('items-center gap-2'):
                        i_score = ui.badge(
                            '0/10', color='teal').props('outline size=md')

                with ui.scroll_area().classes('w-full p-6 flex-grow') as i_scroll_area:
                    i_title = ui.html('Paper Title', sanitize=False).classes(
                        'text-lg font-black text-slate-800 leading-snug mb-2')
                    
                    # Read Source Button
                    i_read_source_btn = ui.button('Read Source', icon='open_in_new').props(
                         'flat dense color=teal-700 size=sm').classes('hidden mb-6 self-start -ml-2')
                    ui.label('CORE FINDINGS').classes(
                        'text-xs font-bold text-slate-400 uppercase mb-2 tracking-wider')
                    i_findings_container = ui.column().classes('w-full gap-3 mb-6')
                    ui.separator().classes('mb-6 opacity-50')
                    ui.label('IMPLICATIONS').classes(
                        'text-xs font-bold text-slate-400 uppercase mb-2 tracking-wider')
                    i_impact_container = ui.column().classes('w-full gap-3')
                    
                    
                with ui.row().classes('w-full p-4 bg-slate-50 border-t border-slate-100 mt-auto justify-between items-center'):
                    with ui.column().classes('gap-0'):
                        ui.label('AUTHORS').classes(
                            'text-[10px] font-bold text-slate-400 tracking-wider mb-1')
                        i_authors_label = ui.label('Loading...').classes(
                            'text-xs text-slate-600 italic leading-tight')
                    
                    with ui.row().classes('items-center gap-2') as i_actions_container:
                        pass

    # Main Content
    
    # Grid Container
    library_container = ui.column().classes('w-full min-h-[calc(100vh-80px)] bg-slate-50 p-6 gap-8')
    
    def render_library():
        library_container.clear()
        favorites = database.get_favorites(user['id'])
        
        with library_container:
            with ui.row().classes('w-full items-center justify-between mb-4'):
                with ui.row().classes('items-center gap-4'):
                    ui.icon('favorite', size='lg').classes('text-red-500')
                    ui.label('My Library').classes('text-3xl font-black text-slate-800')
                    ui.label(f"{len(favorites)} Saved Articles").classes('text-slate-500 font-bold uppercase tracking-wider text-sm')
                
                # Clear Notifications Button
                total_notifications = sum(p.get('new_comments_count', 0) for p in favorites)
                if total_notifications > 0:
                    async def clear_all_notifications():
                        database.mark_all_papers_viewed(user['id'])
                        ui.notify('All notifications cleared!', type='positive')
                        render_library()
                    
                    ui.button('Clear Notifications', icon='done_all', on_click=clear_all_notifications).props('flat dense no-caps color=slate-500').classes('font-bold')

            if not favorites:
                 ui.label("You haven't saved any papers yet.").classes('text-slate-400 italic mt-8')
            else:
                # Handler for removal that also clears inspector
                def handle_remove_paper(p, w):
                     w.delete()
                     nonlocal pinned_paper
                     if pinned_paper == p:
                         pinned_paper = None
                     # Force reset inspector (show default view)
                     if info_view and default_view:
                         info_view.classes(add='hidden')
                         default_view.classes(remove='hidden')
                     # Re-render to update counts if needed
                     render_library()

                grid = ui.grid(columns=2).classes('w-full gap-6')
                with grid:
                    for paper in favorites:
                        # Mark as saved so heart icon shows correctly
                        paper['_is_saved'] = True 
                        
                        # Wrapper for deletion
                        wrapper = ui.element('div').classes('w-full')
                        
                        # Use closure to capture wrapper for deletion
                        def make_card(p, w):
                             display_curated_card(w, p, on_hover=update_inspector,
                                                  on_leave=lambda: start_reset_timer(), 
                                                  on_click=toggle_pin,
                                                  on_unfavorite=lambda _: handle_remove_paper(p, w))
                        make_card(paper, wrapper)
    
    # Initial Render
    render_library()

@ui.page('/profile')
def profile_page():
    # app.storage.user['referrer_path'] = '/profile' - REMOVED
    header(on_topic_click=lambda t: ui.navigate.to(f'/topic/{t}'), 
           on_home_click=lambda: ui.navigate.to('/'), current_path='/profile')
    
    user = auth.get_current_user()
    if not user:
        ui.label('Please login to view your profile.').classes('m-8 text-lg')
        return

    # Fetch profile
    profile = database.get_profile(user['id']) or {}
    
    with ui.column().classes('w-full min-h-screen bg-slate-50 p-8 items-center'):
        with ui.card().classes('w-full max-w-2xl p-8 gap-6'):
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label('Edit Profile').classes('text-2xl font-black text-slate-800')
                
                # Right Side Actions (Avatar + X)
                with ui.row().classes('items-center gap-4'):
                    # Avatar Upload
                    avatar_url = profile.get('avatar_url')
                    
                    # Hidden uploader
                    uploader = ui.upload(auto_upload=True, on_upload=lambda e: handle_avatar_upload(e)).props('accept=.jpg,.jpeg,.png,.webp style="display: none;"')
                    
                    async def handle_avatar_upload(e):
                        # NiceGUI 2.0+ uses e.file, older uses e.content
                        msg = getattr(e, 'file', None) or getattr(e, 'content', None)
                        
                        if not msg:
                            return

                        # Size check
                        size_attr = getattr(msg, 'size', 0)
                        file_size = size_attr() if callable(size_attr) else size_attr
                        if file_size > 5 * 1024 * 1024:
                            ui.notify('File too large (max 5MB)', type='negative')
                            return
                        
                        # Content
                        # If read is a method
                        if callable(getattr(msg, 'read', None)):
                            content = await msg.read()
                        else:
                            content = msg
                        
                        # Determine ext
                        filename = getattr(msg, 'name', 'avatar.png')
                        ext = filename.split('.')[-1].lower()
                        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                            ui.notify('Invalid file type', type='negative')
                            return

                        # Prepare for Cropping
                        try:
                            b64_data = base64.b64encode(content).decode('utf-8')
                            data_url = f"data:image/{ext};base64,{b64_data}"
                        except Exception as err:
                             print(f"Error encoding image: {err}")
                             return

                        # Open Crop Dialog
                        with ui.dialog().props('persistent') as crop_dialog, ui.card().classes('w-auto min-w-[350px] max-w-[90vw] p-0 overflow-hidden flex flex-col'):
                            # Header
                            with ui.row().classes('w-full p-4 bg-slate-50 border-b justify-between items-center'):
                                ui.label('Crop Avatar').classes('font-bold text-lg')
                                ui.button(icon='close', on_click=crop_dialog.close).props('flat round dense')
                            
                            # Cropper Area (Flexible)
                            # We set max constraints so it doesn't overflow screen
                            with ui.element('div').classes('min-w-[300px] min-h-[300px] max-h-[70vh] bg-black relative flex justify-center'):
                                # Image max-height matches container max-height to avoid overflow
                                ui.html(f'<img id="avatar-cropper-img" src="{data_url}" style="max-height: 70vh; max-width: 100%; display: block;">', sanitize=False)
                            
                            # Actions
                            async def save_crop():
                                ui.notify('Processing...', type='info')
                                try:
                                    # Get Crop Data from JS
                                    crop_data = await ui.run_javascript('return window.cropper.getData();', timeout=3.0)
                                    
                                    if not crop_data:
                                        ui.notify('Error getting crop data', type='negative')
                                        return

                                    # Process in Python
                                    with Image.open(io.BytesIO(content)) as img:
                                        # Crop
                                        x = int(crop_data['x'])
                                        y = int(crop_data['y'])
                                        w = int(crop_data['width'])
                                        h = int(crop_data['height'])
                                        
                                        # Sanity bounds
                                        cropped = img.crop((x, y, x+w, y+h))
                                        
                                        # Resize to standard avatar (256x256) (High Quality)
                                        final_img = cropped.resize((256, 256), Image.Resampling.LANCZOS)
                                        
                                        # Save to bytes (PNG for quality)
                                        out_buffer = io.BytesIO()
                                        final_img.save(out_buffer, format='PNG')
                                        final_bytes = out_buffer.getvalue()
                                        
                                        # Upload
                                        token = user.get('access_token')
                                        new_url = database.upload_avatar(user['id'], final_bytes, 'png', access_token=token)
                                        
                                        if new_url:
                                            ui.notify('Avatar updated!', type='positive')
                                            # Update Session
                                            if 'user' in app.storage.user:
                                                app.storage.user['user']['avatar_url'] = new_url
                                                if 'metadata' not in app.storage.user['user']:
                                                     app.storage.user['user']['metadata'] = {}
                                                app.storage.user['user']['metadata']['avatar_url'] = new_url
                                            
                                            crop_dialog.close()
                                            ui.navigate.to('/profile', new_tab=False)
                                        else:
                                            ui.notify('Upload failed', type='negative')

                                except Exception as err:
                                    print(f"Crop error: {err}")
                                    ui.notify('Error processing image', type='negative')

                            with ui.row().classes('w-full p-4 gap-4 justify-between bg-slate-50 border-t'):
                                with ui.row().classes('gap-2'):
                                    ui.button(icon='zoom_out', on_click=lambda: ui.run_javascript('window.cropper.zoom(-0.1)')).props('flat outline round dense color=slate-600')
                                    ui.button(icon='zoom_in', on_click=lambda: ui.run_javascript('window.cropper.zoom(0.1)')).props('flat outline round dense color=slate-600')
                                
                                with ui.row().classes('gap-4'):
                                    ui.button('Cancel', on_click=crop_dialog.close).props('flat text-color=slate-600')
                                    ui.button('Save Avatar', on_click=save_crop).classes('bg-slate-900 text-white')
                        
                        crop_dialog.open()
                        # Initialize Cropper JS
                        await ui.run_javascript('''
                            if (window.cropper) { window.cropper.destroy(); }
                            var image = document.getElementById('avatar-cropper-img');
                            window.cropper = new Cropper(image, {
                                aspectRatio: 1,
                                viewMode: 0, 
                                dragMode: 'move',
                                autoCropArea: 1,
                                background: false
                            });
                        ''', timeout=10.0)

                    # Avatar Circle
                    with ui.button(on_click=lambda: uploader.run_method('pickFiles')).props('round flat p-0').classes('overflow-hidden w-12 h-12 border-2 border-slate-200'):
                        if avatar_url:
                            ui.image(avatar_url).classes('w-full h-full object-cover')
                        else:
                            ui.icon('account_circle', size='xl').classes('text-slate-300')
                        ui.tooltip('Click to change profile picture')
                    
                    # X Link Button (Success or Connect)
                    current_x = profile.get('x_handle')
                    if current_x:
                        with ui.chip(icon='check', color='slate-100').props('removable').classes('text-slate-600') as chip:
                            with chip.add_slot('avatar'):
                                 ui.image('/assets/x_logo.png')
                            ui.label(current_x)
                            # Optional: Add logic to unlink if chip is removed
                            chip.on('remove', lambda: ui.notify('To unlink, please contact support.', type='warning')) 
                    else:
                        ui.button(icon='img:/assets/x_logo.png', on_click=auth.login_with_twitter).props('flat round color=slate-800 size=xl').tooltip('Connect X Account')

            with ui.column().classes('w-full gap-4'):
                ui.label('Email').classes('text-sm text-slate-400 font-bold uppercase')
                ui.label(user.get('email')).classes('text-slate-700 font-medium')
                
                ui.separator()
                
                username = ui.input(label='Username', value=profile.get('username', '')).classes('w-full')
                fullname = ui.input(label='Full Name', value=profile.get('full_name', '')).classes('w-full')
                
                async def save_profile():
                    updates = {
                        'username': username.value,
                        'full_name': fullname.value,
                        'updated_at': 'now()'
                    }
                    res = database.update_profile(user['id'], updates)
                    if res:
                         ui.notify('Profile updated!', type='positive')
                    else:
                         ui.notify('Error updating profile.', type='negative')

                ui.button('Save Changes', on_click=save_profile).props('unelevated color=slate-900 text-color=white').classes('w-full')


if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.environ.get("PORT", 8080))
    ui.run(title='Skim', favicon='assets/logo.png', port=port,
           host='0.0.0.0', storage_secret='skim_secret_key', reload=False)
