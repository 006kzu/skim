from nicegui import ui, run, app
import scholar_api
import database
import topics
import os

# --- INITIALIZATION ---
database.init_db()
app.add_static_files('/assets', 'assets')

# --- ICON RESOLVER ---
ICON_ALIASES = {
    "artificial intelligence": "artificial_intelligence",
    "ai": "ai",
    "machine learning": "ai",
    "deep learning": "ai",
}


def get_category_icon(category_name):
    if not category_name:
        return '/assets/logo.png'

    clean = category_name.lower().strip()
    file_friendly = clean.replace(" & ", "_and_").replace(" ", "_")

    if os.path.exists(f"assets/{file_friendly}.png"):
        return f"assets/{file_friendly}.png"

    if clean in ICON_ALIASES:
        alias = ICON_ALIASES[clean]
        if os.path.exists(f"assets/{alias}.png"):
            return f"assets/{alias}.png"

    return '/assets/logo.png'


# --- UI COMPONENTS ---

def display_arxiv_card(container, paper):
    with container:
        with ui.card().classes('w-full hover:shadow-lg transition-all border border-slate-200'):
            with ui.row().classes('justify-between w-full'):
                ui.label('ArXiv Search').classes(
                    'text-xs text-teal-600 font-bold uppercase')
                ui.label(paper['date']).classes('text-xs text-slate-400')
            ui.label(paper['title']).classes(
                'text-lg font-bold leading-tight mt-2 text-slate-800')
            ui.label(f"Authors: {paper['authors']}").classes(
                'text-sm text-slate-500 mt-1')

            with ui.expansion('Read Abstract', icon='description').classes('w-full text-slate-500 text-sm'):
                ui.markdown(paper['summary'])

            ai_result_area = ui.markdown().classes(
                'text-sm text-slate-800 bg-teal-50 p-4 rounded-lg hidden mt-2 w-full')

            ui.separator().classes('mt-4 mb-2')
            with ui.row().classes('w-full justify-between items-center'):
                if paper.get('link'):
                    ui.button('PDF', icon='open_in_new').props(
                        f'href="{paper["link"]}" target="_blank" flat dense color=grey')

                async def run_ai_skim():
                    skim_btn.props('loading')
                    result = await run.io_bound(scholar_api.analyze_with_ai, paper['title'], paper['summary'])
                    ai_result_area.content = result
                    ai_result_area.classes(remove='hidden')
                    skim_btn.props(remove='loading')

                skim_btn = ui.button('Skim with AI', icon='bolt', on_click=run_ai_skim).props(
                    'unelevated color=teal-700 text-color=white')
            ai_result_area.move(container)


def display_curated_card(container, paper, on_hover=None, on_leave=None, on_click=None):
    with container:
        card = ui.card().classes(
            'w-full h-full border-l-4 border-teal-500 shadow-sm hover:shadow-md transition-all duration-300 cursor-pointer flex flex-col justify-between group')

        if on_click:
            card.on('click', lambda: on_click(paper))

        with card:
            with ui.column().classes('w-full gap-1'):
                with ui.row().classes('justify-between w-full items-start mb-2'):
                    category = paper.get('category', 'General')
                    icon_path = get_category_icon(category)

                    with ui.row().classes('items-center gap-2'):
                        ui.image(icon_path).classes('w-5 h-5 opacity-80')
                        ui.label(category).classes(
                            'text-[10px] font-bold text-teal-600 uppercase tracking-wide')

                    ui.badge(f"{paper.get('score', '?')}",
                             color='teal').props('outline size=xs')

                ui.label(paper.get('summary', 'No summary')).classes(
                    'text-md font-bold leading-tight text-slate-900 group-hover:text-teal-800 transition-colors')
                ui.label(paper['title']).classes(
                    'text-[10px] text-slate-400 italic mt-1 line-clamp-1')

            url = paper.get('url') or paper.get('link')
            if url:
                with ui.row().classes('mt-3 w-full justify-end'):
                    ui.button('Source', icon='link').props(f'href="{url}" target="_blank" flat dense size=sm color=teal').on(
                        'click', lambda e: e.stop_propagation())

        if on_hover:
            card.on('mouseenter', lambda: on_hover(paper))
        if on_leave:
            card.on('mouseleave', on_leave)


def header(on_topic_click=None, on_home_click=None, on_search=None):
    with ui.header().classes('bg-white text-slate-800 border-b border-slate-200 elevation-0'):
        with ui.row().classes('w-full items-center justify-between h-20 px-6 no-wrap gap-8'):

            # 1. LEFT: Logo
            with ui.row().classes('items-center cursor-pointer min-w-max').on('click', on_home_click):
                ui.image('/assets/logo.png').classes('w-10 h-10 mr-3')
                with ui.column().classes('gap-0'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label('Skim').classes(
                            'text-xl font-black tracking-tight text-slate-900')
                        ui.label('v3.4').classes(
                            'bg-teal-100 text-teal-800 text-[10px] px-1.5 py-0.5 rounded font-bold')
                    ui.label('Academic Resources').classes(
                        'text-[9px] font-bold text-teal-600 tracking-widest uppercase')

            # 2. MIDDLE: Search Bar
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

            # 3. RIGHT: Research Hub + Nav Links
            with ui.row().classes('items-center gap-4 min-w-max'):

                # --- RESEARCH HUB BUTTON ---
                hub_btn = ui.button('Research Hub', icon='apps').props('flat no-caps color=teal-700 size=md icon-right=arrow_drop_down').classes(
                    'font-bold tracking-tight bg-teal-50 hover:bg-teal-100 rounded-lg px-3')

                # Helper logic for Hover Bridge
                hub_timer = None

                def cancel_hub_timer():
                    nonlocal hub_timer
                    if hub_timer:
                        hub_timer.cancel()
                        hub_timer = None

                def start_hub_timer():
                    nonlocal hub_timer
                    cancel_hub_timer()
                    # 200ms grace period to move from button to menu
                    hub_timer = ui.timer(
                        0.2, lambda: mega_menu.close(), once=True)

                # MEGA MENU
                with ui.menu().classes('bg-white border border-slate-200 shadow-2xl rounded-xl p-8 w-[1000px] max-w-[95vw]') as mega_menu:
                    mega_menu.props('no-parent-event')

                    with ui.row().classes('w-full justify-between items-start no-wrap gap-6'):
                        for hub_name, topic_list in topics.TOPIC_HUBS.items():
                            hub_icon = get_category_icon(hub_name)

                            with ui.column().classes('flex-1 gap-4'):
                                with ui.row().classes('items-center gap-2 mb-1 border-b border-slate-100 pb-2 w-full'):
                                    ui.image(hub_icon).classes(
                                        'w-6 h-6 opacity-80')
                                    ui.label(hub_name).classes(
                                        'text-xs font-black text-slate-400 uppercase tracking-wider')

                                with ui.column().classes('gap-1 w-full'):
                                    for topic in topic_list:
                                        topic_icon = get_category_icon(topic)
                                        with ui.menu_item(on_click=lambda t=topic: on_topic_click(t)).classes('w-full rounded-md hover:bg-teal-50 transition-all duration-200 p-1 hover:scale-105 origin-left'):
                                            with ui.row().classes('items-center gap-3 no-wrap'):
                                                ui.image(topic_icon).classes(
                                                    'w-5 h-5 opacity-90')
                                                ui.label(topic).classes(
                                                    'text-xs font-bold text-teal-700 leading-tight')

                # --- EVENTS for Hover Bridge ---
                hub_btn.on('mouseenter', lambda: [
                           cancel_hub_timer(), mega_menu.open()])
                hub_btn.on('mouseleave', start_hub_timer)

                mega_menu.on('mouseenter', cancel_hub_timer)
                mega_menu.on('mouseleave', start_hub_timer)

                ui.separator().props('vertical').classes('h-6 mx-2 opacity-30')
                ui.link('Dashboard', '/').classes(
                    'text-slate-500 font-bold text-xs hover:text-teal-600 transition-colors uppercase tracking-wide')
                ui.link('Library', '/saved').classes(
                    'text-slate-500 font-bold text-xs hover:text-teal-600 transition-colors uppercase tracking-wide')


@ui.page('/')
def dashboard():
    ui.add_head_html('''
    <style>
        .q-item__section--avatar { min-width: 50px !important; }
        .q-item__section--avatar .q-icon { font-size: 40px !important; }
        .q-item__section--avatar img { width: 40px !important; height: 40px !important; }
        ::-webkit-scrollbar { height: 0px; background: transparent; }
    </style>
    ''')

    # --- STATE ---
    feed_label = None
    feed_grid = None
    pinned_paper = None
    results_grid = None

    # Inspector UI Refs
    i_category = None
    i_icon = None
    i_score = None
    i_title = None  # NEW: Reference for the title label
    i_lock_btn = None
    i_findings_container = None
    i_impact_container = None
    i_authors_label = None
    default_view = None
    info_view = None

    reset_timer = None

    # --- LOGIC ---

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

        # CHANGED: Reduced delay to 0.1s.
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
            i_icon.set_source(get_category_icon(cat))
        if i_score:
            i_score.text = f"{paper.get('score', '?')}/10"

        # --- UPDATE TITLE ---
        if i_title:
            i_title.text = paper['title']

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
                    display_curated_card(
                        feed_grid,
                        paper,
                        on_hover=update_inspector,
                        on_leave=lambda: start_reset_timer(),
                        on_click=toggle_pin
                    )

    def load_topic_feed(topic):
        nonlocal pinned_paper
        pinned_paper = None
        hard_reset_inspector()
        papers = database.get_papers_by_topic(topic)
        render_feed(papers, f'Topic: {topic}')

    def load_home_feed():
        nonlocal pinned_paper
        pinned_paper = None
        hard_reset_inspector()
        top_papers = database.get_top_rated_papers(limit=12)
        render_feed(top_papers, 'Global Top Hits (Recent)')

    # --- UI STRUCTURE ---

    header(on_topic_click=load_topic_feed,
           on_home_click=load_home_feed, on_search=perform_search)

    # CHANGED: ui.left_drawer -> ui.right_drawer
    # CHANGED: border-r -> border-l
    drawer = ui.right_drawer(value=True).props('width=450').classes(
        'bg-slate-50 border-l border-slate-200 p-6 column no-wrap gap-4')

    drawer.on('mouseenter', cancel_reset_timer)
    drawer.on('mouseleave', lambda: start_reset_timer())

    with drawer:
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Inspector').classes(
                'text-sm font-bold text-slate-400 uppercase tracking-wider')
            ui.icon('manage_search', color='slate-300')

        with ui.column().classes('w-full flex-grow relative transition-all overflow-hidden'):

            with ui.column().classes('w-full h-full items-center justify-center text-center') as default_view:
                ui.image('/assets/logo.png').classes('w-32 h-32 opacity-20 mb-4')
                ui.label('Hover to Preview').classes(
                    'text-lg font-bold text-slate-400')
                ui.label('Click to Pin').classes(
                    'text-sm font-bold text-teal-500 uppercase tracking-widest')

            with ui.column().classes('hidden w-full flex-grow bg-white rounded-xl border border-slate-200 shadow-md animate-fade overflow-hidden') as info_view:

                with ui.row().classes('w-full justify-between items-center p-6 border-b border-slate-100 bg-slate-50'):
                    with ui.row().classes('items-center gap-3'):
                        i_icon = ui.image().classes('w-8 h-8 opacity-80')
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
                    # --- TITLE LABEL ADDED HERE ---
                    i_title = ui.label('Paper Title').classes(
                        'text-lg font-black text-slate-800 leading-snug mb-6')

                    ui.label('CORE FINDINGS').classes(
                        'text-xs font-bold text-slate-400 uppercase mb-2 tracking-wider')
                    i_findings_container = ui.column().classes('w-full gap-3 mb-6')

                    ui.separator().classes('mb-6 opacity-50')

                    ui.label('IMPLICATIONS').classes(
                        'text-xs font-bold text-slate-400 uppercase mb-2 tracking-wider')
                    i_impact_container = ui.column().classes('w-full gap-3')

                with ui.row().classes('w-full p-4 bg-slate-50 border-t border-slate-100 mt-auto'):
                    with ui.column().classes('gap-0 w-full'):
                        ui.label('AUTHORS').classes(
                            'text-[10px] font-bold text-slate-400 tracking-wider mb-1')
                        i_authors_label = ui.label('Loading...').classes(
                            'text-xs text-slate-600 italic leading-tight')

    # --- CONTENT ---
    with ui.column().classes('w-full p-6 gap-8'):

        # Results Grid
        results_grid = ui.grid(columns=1).classes('w-full gap-4 hidden')

        with ui.row().classes('w-full items-center justify-between mb-4'):
            feed_label = ui.label('Loading...').classes(
                'text-2xl font-bold text-slate-800')
            ui.button('Reset', icon='refresh', on_click=load_home_feed).props(
                'flat dense color=slate-400')

        feed_grid = ui.grid(columns=2).classes('w-full gap-4')

    ui.timer(0.1, load_home_feed, once=True)


if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.environ.get("PORT", 8080))
    ui.run(title='Skim', favicon='assets/logo.png', port=port, host='0.0.0.0')
