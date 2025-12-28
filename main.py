from nicegui import ui, run, app
import scholar_api
import database
import topics
import os

# --- INITIALIZATION ---
database.init_db()
app.add_static_files('/assets', 'assets')

# --- ICON RESOLVER LOGIC ---
ICON_ALIASES = {
    "artificial intelligence": "ai",
    "machine learning": "ai",
    "deep learning": "ai",
}


def get_category_icon(category_name):
    if not category_name:
        return '/assets/logo.png'
    clean_name = category_name.lower().strip()
    file_name = clean_name.replace(" ", "_")

    def get_versioned_path(path):
        if os.path.exists(path):
            return f"/{path}?v={os.path.getmtime(path)}"
        return None

    specific_path = f"assets/{file_name}.png"
    if found := get_versioned_path(specific_path):
        return found

    if clean_name in ICON_ALIASES:
        alias_path = f"assets/{ICON_ALIASES[clean_name]}.png"
        if found := get_versioned_path(alias_path):
            return found

    for hub, topic_list in topics.TOPIC_HUBS.items():
        if any(t.lower() == clean_name for t in topic_list):
            hub_path = f"assets/{hub.lower().replace(' ', '_')}.png"
            if found := get_versioned_path(hub_path):
                return found

    return '/assets/logo.png'


# --- UI COMPONENTS ---

def display_arxiv_card(container, paper):
    """
    ArXiv cards don't use the inspector panel since they lack pre-computed AI insights.
    """
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
                url = paper.get('link')
                if url:
                    ui.button('PDF', icon='open_in_new').props(
                        f'href="{url}" target="_blank" flat dense color=grey')

                async def run_ai_skim():
                    skim_btn.props('loading')
                    result = await run.io_bound(scholar_api.analyze_with_ai, paper['title'], paper['summary'])
                    ai_result_area.content = result
                    ai_result_area.classes(remove='hidden')
                    skim_btn.props(remove='loading')

                skim_btn = ui.button('Skim with AI', icon='bolt', on_click=run_ai_skim).props(
                    'unelevated color=teal-700 text-color=white')
            ai_result_area.move(container)


def display_curated_card(container, paper, on_hover=None, on_leave=None):
    """
    Displays a feed card. 
    Crucially, it accepts callbacks to update the side panel.
    """
    with container:
        # We assign the card to a variable so we can bind events to it
        card = ui.card().classes(
            'w-full border-l-4 border-teal-500 shadow-sm hover:shadow-md transition-all duration-300 cursor-default')

        with card:
            # Header
            with ui.row().classes('justify-between w-full items-start'):
                category = paper.get('category', 'General')
                icon_path = get_category_icon(category)

                with ui.row().classes('items-center gap-2'):
                    ui.image(icon_path).classes('w-6 h-6 opacity-80')
                    ui.label(category).classes(
                        'text-xs font-bold text-teal-600 uppercase tracking-wide')

                ui.badge(f"Score: {paper.get('score', '?')}/10",
                         color='teal').props('outline')

            # Content
            ui.label(paper.get('summary', 'No summary')).classes(
                'text-lg font-bold leading-tight mt-2 text-slate-900')
            ui.label(paper['title']).classes(
                'text-xs text-slate-400 mt-2 italic')

            # Footer
            url = paper.get('url') or paper.get('link')
            if url:
                with ui.row().classes('mt-4 w-full justify-end'):
                    ui.button('Read Source', icon='link').props(
                        f'href="{url}" target="_blank" flat dense color=teal')

        # --- EVENT BINDING ---
        # When mouse enters this card, call the function that updates the sidebar
        if on_hover:
            card.on('mouseenter', lambda: on_hover(paper))

        # When mouse leaves, reset the sidebar
        if on_leave:
            card.on('mouseleave', on_leave)


def header():
    with ui.header().classes('items-center justify-between bg-white text-slate-800 border-b border-slate-200 elevation-0 h-24'):
        with ui.row().classes('items-center ml-4'):
            ui.image('/assets/logo.png').classes('w-20 h-20 mr-4')
            with ui.column().classes('gap-0'):
                ui.label('Skim').classes(
                    'text-2xl font-black tracking-tight text-slate-900')
                ui.label('Academic Resources (Only the Good Ones)').classes(
                    'text-xs font-bold text-teal-600 tracking-widest uppercase')

        with ui.row().classes('mr-6 gap-6'):
            ui.link('Dashboard', '/').classes(
                'text-slate-600 font-medium hover:text-teal-600 transition-colors')
            ui.link('Library', '/saved').classes(
                'text-slate-600 font-medium hover:text-teal-600 transition-colors')


def sidebar(on_topic_click):
    with ui.left_drawer(value=True).classes('bg-slate-50 border-r border-slate-200 p-4'):
        ui.label('Research Hubs').classes(
            'text-xs font-bold text-slate-400 uppercase mb-4 tracking-wider')
        for hub_name, topic_list in topics.TOPIC_HUBS.items():
            icon_path = get_category_icon(hub_name)
            with ui.expansion(hub_name, icon=f'img:{icon_path}').classes('w-full text-slate-800 font-bold'):
                for topic in topic_list:
                    ui.button(topic).props('flat align=left dense').classes(
                        'w-full text-teal-600 font-medium text-sm pl-8 hover:text-teal-800 transition-colors').on_click(lambda t=topic: on_topic_click(t))


@ui.page('/')
def dashboard():
    # Helper CSS for icons and sticky positioning
    ui.add_head_html('''
    <style>
        .q-item__section--avatar { min-width: 50px !important; }
        .q-item__section--avatar .q-icon { font-size: 40px !important; }
        .q-item__section--avatar img { width: 40px !important; height: 40px !important; }
    </style>
    ''')

    header()

    # --- THE INSPECTOR PANEL (Right Sidebar) ---
    # We define this first so we can reference it in the feed logic.
    # It is 'fixed' or 'sticky' so it stays on screen.

    with ui.row().classes('w-full max-w-7xl mx-auto p-6 gap-8 items-start relative'):

        # 1. LEFT COLUMN: The Feed
        left_col = ui.column().classes('flex-grow w-full md:w-2/3')

        # 2. RIGHT COLUMN: The Sticky Inspector
        # 'sticky top-28' means it will stick 28px/units from the top of the viewport
        right_col = ui.card().classes(
            'hidden md:flex w-1/3 sticky top-28 h-auto min-h-[500px] border border-teal-100 bg-white shadow-lg p-0 overflow-hidden')

        with right_col:
            # -- STATE A: Default (Logo) --
            default_view = ui.column().classes(
                'w-full h-96 items-center justify-center text-slate-300 transition-opacity duration-500')
            with default_view:
                ui.label('SKIM').classes(
                    'text-6xl font-black opacity-10 tracking-tighter')
                ui.icon('touch_app').classes('text-4xl opacity-20 mt-4')
                ui.label('HOVER TO INSPECT').classes(
                    'text-xs font-bold tracking-[0.3em] mt-2 opacity-40')

            # -- STATE B: Active (Paper Details) --
            # Initially hidden
            info_view = ui.column().classes('hidden w-full h-full p-6 bg-slate-50/50')

            # Placeholder elements we will update dynamically
            with info_view:
                # Header area
                with ui.row().classes('w-full justify-between items-start mb-4'):
                    i_category = ui.label('CATEGORY').classes(
                        'text-xs font-bold text-teal-600 uppercase tracking-wide')
                    i_score = ui.badge('0/10', color='teal').props('outline')

                i_title = ui.label('Paper Title').classes(
                    'text-xl font-bold text-slate-900 leading-tight mb-6')

                # Findings Area
                ui.label('CORE FINDINGS').classes(
                    'text-xs font-bold text-slate-400 uppercase mb-2 tracking-wider')
                i_findings_container = ui.column().classes('w-full gap-2 mb-6')

                # Implications Area
                ui.label('IMPACT ANALYSIS').classes(
                    'text-xs font-bold text-slate-400 uppercase mb-2 tracking-wider')
                i_impact_container = ui.column().classes('w-full gap-2')

    # --- INTERACTION LOGIC ---

    def update_inspector(paper):
        """Populate the right sidebar with data from the hovered paper."""
        default_view.classes(add='hidden')
        info_view.classes(remove='hidden')

        # Update simple fields
        i_category.text = paper.get('category', 'Unknown')
        i_score.text = f"Impact: {paper.get('score', '?')}/10"
        i_title.text = paper['title']

        # Re-build Findings List
        i_findings_container.clear()
        with i_findings_container:
            for f in paper.get('key_findings', []):
                ui.label(f"• {f}").classes(
                    'text-sm text-slate-700 leading-snug')

        # Re-build Impact List
        i_impact_container.clear()
        with i_impact_container:
            imps = paper.get('implications', [])
            if isinstance(imps, list):
                for imp in imps:
                    ui.label(f"➔ {imp}").classes(
                        'text-sm text-slate-800 font-medium leading-snug')
            else:
                ui.markdown(str(imps)).classes('text-sm')

    def reset_inspector():
        """Revert to the logo view."""
        info_view.classes(add='hidden')
        default_view.classes(remove='hidden')

    # --- FEED LOGIC (Left Column) ---

    def render_feed(papers, title):
        feed_label.set_text(title)
        feed_grid.clear()

        if not papers:
            with feed_grid:
                with ui.column().classes('w-full items-center py-12 text-slate-400'):
                    ui.icon('inbox', size='48px').classes('mb-4')
                    ui.label('No papers found yet.').classes('text-lg')
            return

        with feed_grid:
            for paper in papers:
                # PASS THE CALLBACKS HERE
                display_curated_card(
                    feed_grid,
                    paper,
                    on_hover=update_inspector,
                    on_leave=reset_inspector
                )

    def load_topic_feed(topic):
        papers = database.get_papers_by_topic(topic)
        render_feed(papers, f'Topic: {topic}')

    def load_home_feed():
        top_papers = database.get_top_rated_papers(limit=12)
        render_feed(top_papers, 'Global Top Hits (Recent)')

    # --- ASSEMBLE LEFT COLUMN ---
    with left_col:
        ui.label('Deep Search').classes(
            'text-2xl font-bold text-slate-800 mb-4')
        with ui.row().classes('w-full max-w-2xl gap-0'):
            search_input = ui.input(placeholder='Search ArXiv (e.g. "Prosthetics")').props(
                'outlined').classes('flex-grow bg-white')

            async def perform_search():
                query = search_input.value
                if not query:
                    return
                ui.notify(f'Searching ArXiv for "{query}"...')
                results_grid.clear()
                papers = await run.io_bound(scholar_api.search_arxiv, query)
                if not papers:
                    ui.notify('No results found.', type='warning')
                with results_grid:
                    for paper in papers:
                        display_arxiv_card(results_grid, paper)

            search_btn = ui.button(icon='search', on_click=perform_search).props(
                'color=blue-grey-9 size=lg square')
            search_input.on('keydown.enter', perform_search)

        results_grid = ui.grid(columns=1).classes('w-full gap-4 mt-6')
        ui.separator().classes('my-12')

        with ui.row().classes('w-full items-center justify-between mb-4'):
            feed_label = ui.label('Loading...').classes(
                'text-2xl font-bold text-slate-800')
            ui.button('Top Hits', icon='home', on_click=load_home_feed).props(
                'outline color=teal')

        # Changed to 1 column for better readability since we have a sidebar now,
        # or we can keep 2 if the screen is very wide. Let's stick to 1 or 2 depending on width.
        # Actually, since left col is 2/3 of screen, 2 columns might be tight. 1 is safer/cleaner.
        feed_grid = ui.grid(columns=1).classes('w-full gap-4')

    # --- INIT ---
    sidebar(on_topic_click=load_topic_feed)
    ui.timer(0.1, load_home_feed, once=True)


if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.environ.get("PORT", 8080))
    ui.run(title='Skim', favicon='assets/logo.png', port=port, host='0.0.0.0')
