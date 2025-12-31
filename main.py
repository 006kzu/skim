from nicegui import ui, run, app
import scholar_api
import database
import topics
import os
import re

# --- INITIALIZATION ---
database.init_db()
app.add_static_files('/assets', 'assets')

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
        return f"assets/{file_friendly}.png"

    # 2. Alias Match
    if clean in ICON_ALIASES:
        alias = ICON_ALIASES[clean]
        if alias in AVAILABLE_ICONS:
            return f"assets/{alias}.png"

    # 3. Smart Fuzzy Match
    words = clean.split(' ')
    for word in words:
        if word in AVAILABLE_ICONS:
            return f"assets/{word}.png"

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
            with ui.row().classes('justify-between w-full'):
                ui.label('ArXiv Search').classes(
                    f"text-xs font-bold uppercase {theme['accent_color']}")
                ui.label(paper.get('date', '')).classes(
                    f"text-xs {theme['text_meta']}")

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


def display_curated_card(container, paper, on_hover=None, on_leave=None, on_click=None):
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

            with ui.column().classes('w-full gap-3'):
                title_text = paper.get('title', 'Untitled Paper')
                highlights = paper.get('title_highlights') or []
                processed_title = highlight_title(
                    title_text, highlights, theme['highlight_hex'])

                ui.html(processed_title, sanitize=False).classes(
                    f"text-xl font-black leading-tight line-clamp-3 w-full {theme['text_title']}")
                ui.label(paper.get('summary', 'No summary')).classes(
                    f"text-sm leading-relaxed line-clamp-6 w-full {theme['text_body']}")

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


def header(on_topic_click=None, on_home_click=None, on_search=None):
    with ui.header().classes('bg-white text-slate-800 border-b border-slate-200 elevation-0'):
        with ui.row().classes('w-full items-center justify-between h-20 px-6 no-wrap gap-8'):
            with ui.row().classes('items-center cursor-pointer min-w-max').on('click', on_home_click):
                ui.image('/assets/logo.png').classes('w-10 h-10 mr-3')
                with ui.column().classes('gap-0'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label('Skim').classes(
                            'text-xl font-black tracking-tight text-slate-900')
                        ui.label('v3.4').classes(
                            'bg-slate-200 text-slate-700 text-[10px] px-1.5 py-0.5 rounded font-bold')
                    ui.label('Academic Resources').classes(
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

                with ui.menu().classes('bg-white border border-slate-200 shadow-2xl rounded-xl p-8 w-[1000px] max-w-[95vw]') as mega_menu:
                    mega_menu.props('no-parent-event')
                    with ui.row().classes('w-full justify-between items-start no-wrap gap-6'):
                        for hub_name, topic_list in topics.TOPIC_HUBS.items():
                            hub_icon = get_category_icon(hub_name)
                            with ui.column().classes('flex-1 gap-4'):
                                with ui.row().classes('items-center gap-2 mb-1 border-b border-slate-100 pb-2 w-full'):
                                    if hub_icon:
                                        ui.image(hub_icon).classes(
                                            'w-6 h-6 opacity-60 grayscale')
                                    else:
                                        ui.icon('category').classes(
                                            'text-slate-300 text-lg')
                                    ui.label(hub_name).classes(
                                        'text-xs font-black text-slate-400 uppercase tracking-wider')
                                with ui.column().classes('gap-1 w-full'):
                                    for topic in topic_list:
                                        topic_icon = get_category_icon(topic)
                                        with ui.menu_item(on_click=lambda t=topic: on_topic_click(t)).classes('w-full rounded-md hover:bg-slate-50 transition-all duration-200 p-1 hover:scale-105 origin-left'):
                                            with ui.row().classes('items-center gap-3 no-wrap'):
                                                if topic_icon:
                                                    ui.image(topic_icon).classes(
                                                        'w-5 h-5 opacity-70 grayscale')
                                                else:
                                                    ui.icon('circle').classes(
                                                        'text-slate-300 text-xs')
                                                ui.label(topic).classes(
                                                    'text-xs font-bold text-slate-700 leading-tight')

                hub_btn.on('mouseenter', lambda: [
                           cancel_hub_timer(), mega_menu.open()])
                hub_btn.on('mouseleave', start_hub_timer)
                mega_menu.on('mouseenter', cancel_hub_timer)
                mega_menu.on('mouseleave', start_hub_timer)

                ui.separator().props('vertical').classes('h-6 mx-2 opacity-30')
                ui.link('Library', '/saved').classes(
                    'text-slate-500 font-bold text-xs hover:text-slate-800 transition-colors uppercase tracking-wide')


# --- ROOT DASHBOARD (CAROUSEL + IMPACT GUIDE) ---
@ui.page('/')
def dashboard():
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
           on_home_click=go_home, on_search=notify_search)

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
                                        f"{theme['text_title']} text-xl font-black leading-tight line-clamp-2")

                                    summary = paper.get(
                                        'summary', 'No summary available.')
                                    ui.label(summary).classes(
                                        f"{theme['text_body']} text-xs leading-relaxed line-clamp-4")

                                    with ui.row().classes('items-center gap-4'):
                                        ui.button('View Analysis', icon='query_stats',
                                                  on_click=lambda p=paper: go_topic(p.get('topic', 'General'))).props('unelevated dense size=sm color=teal-600')

                                        if paper.get('url'):
                                            ui.button('Read Source', icon='open_in_new',
                                                      on_click=lambda u=paper['url']: ui.open(u)).props('flat dense size=sm color=teal-600')

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


@ui.page('/topic/{topic_name}')
def topic_pages(topic_name: str):
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
    i_authors_label = None
    default_view = None
    info_view = None
    i_read_source_btn = None

    reset_timer = None

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
            i_title.text = paper['title']
        if i_authors_label:
            authors = paper.get('authors', 'Unknown')
            if isinstance(authors, list):
                authors = ", ".join(authors)
            i_authors_label.text = authors
        if i_read_source_btn:
            url = paper.get('url') or paper.get('link')
            if url:
                i_read_source_btn.props(f'href="{url}" target="_blank"')
                i_read_source_btn.classes(remove='hidden')
            else:
                i_read_source_btn.classes(add='hidden')
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
           on_search=perform_search)

    drawer = ui.right_drawer(value=True).props('width=450').classes(
        'bg-slate-50 border-l border-slate-200 p-6 column no-wrap gap-4')
    drawer.on('mouseenter', cancel_reset_timer)
    drawer.on('mouseleave', lambda: start_reset_timer())

    with drawer:
        with ui.row().classes('w-full items-center gap-2'):
            ui.icon('manage_search').classes('text-base text-slate-400')
            ui.label('Inspector').classes(
                'text-sm font-bold text-slate-400 uppercase tracking-wider')

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
                        i_lock_btn = ui.button(icon='lock_open').props(
                            'flat round dense color=slate-300').on('click', lambda: toggle_pin(None))
                        ui.tooltip(
                            'Click card to Pin/Unpin').classes('bg-slate-800 text-white')

                with ui.scroll_area().classes('w-full p-6 flex-grow'):
                    i_title = ui.label('Paper Title').classes(
                        'text-lg font-black text-slate-800 leading-snug mb-6')
                    ui.label('CORE FINDINGS').classes(
                        'text-xs font-bold text-slate-400 uppercase mb-2 tracking-wider')
                    i_findings_container = ui.column().classes('w-full gap-3 mb-6')
                    ui.separator().classes('mb-6 opacity-50')
                    ui.label('IMPLICATIONS').classes(
                        'text-xs font-bold text-slate-400 uppercase mb-2 tracking-wider')
                    i_impact_container = ui.column().classes('w-full gap-3')

                with ui.row().classes('w-full p-4 bg-slate-50 border-t border-slate-100 mt-auto justify-between items-end'):
                    with ui.column().classes('gap-0'):
                        ui.label('AUTHORS').classes(
                            'text-[10px] font-bold text-slate-400 tracking-wider mb-1')
                        i_authors_label = ui.label('Loading...').classes(
                            'text-xs text-slate-600 italic leading-tight')
                    i_read_source_btn = ui.button('Read Source', icon='open_in_new').props(
                        'flat dense color=teal-700 size=sm').classes('hidden')

    with ui.column().classes('w-full p-6 gap-8'):
        results_grid = ui.grid(columns=1).classes('w-full gap-4 hidden')
        with ui.row().classes('w-full items-center justify-between mb-4'):
            feed_label = ui.label('Loading...').classes(
                'text-2xl font-bold text-slate-800')
            # REMOVED RESET BUTTON
        feed_grid = ui.grid(columns=2).classes('w-full gap-4')

    ui.timer(0.1, lambda: load_topic_feed(topic_name), once=True)


if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.environ.get("PORT", 8080))
    ui.run(title='Skim', favicon='assets/logo.png', port=port,
           host='0.0.0.0', storage_secret='skim_secret_key')
