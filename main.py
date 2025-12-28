from nicegui import ui, run, app
import scholar_api
import database
import topics
import os

# --- INITIALIZATION ---
database.init_db()

# 1. SERVE STATIC FILES
app.add_static_files('/assets', 'assets')

# --- CONFIGURATION ---
CATEGORY_ICONS = {
    "Engineering": "img:/assets/engineering.png",
    "Future Tech": "img:/assets/future_tech.png",
    "Life Sciences": "img:/assets/life_sciences.png",
    "Hard Sciences": "img:/assets/hard_sciences.png"
}

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

                # FIXED: Capture URL in lambda to ensure link works
                url = paper.get('link')
                ui.button('PDF', icon='open_in_new', on_click=lambda url=url: ui.open(
                    url, new_tab=True)).props('flat dense color=grey')

                async def run_ai_skim():
                    skim_btn.props('loading')
                    result = await run.io_bound(scholar_api.analyze_with_ai, paper['title'], paper['summary'])
                    ai_result_area.content = result
                    ai_result_area.classes(remove='hidden')
                    skim_btn.props(remove='loading')
                skim_btn = ui.button('Skim with AI', icon='bolt', on_click=run_ai_skim).props(
                    'unelevated color=teal-700 text-color=white')
            ai_result_area.move(container)


def display_curated_card(container, paper):
    with container:
        # UPDATED: Added 'group' class to enable hover effects on children
        with ui.card().classes('w-full border-l-4 border-teal-500 shadow-sm group hover:shadow-md transition-all duration-300'):
            # Header
            with ui.row().classes('justify-between w-full items-start'):
                # UPDATED: Added Category Icon (Image)
                category = paper.get('category', 'General')
                icon_src = CATEGORY_ICONS.get(category, None)

                with ui.row().classes('items-center gap-2'):
                    if icon_src:
                        # Clean up "img:" prefix for ui.image
                        clean_src = icon_src.replace('img:', '')
                        ui.image(clean_src).classes('w-6 h-6 opacity-70')

                    ui.label(category).classes(
                        'text-xs font-bold text-teal-600 uppercase tracking-wide')

                ui.badge(f"Score: {paper.get('score', '?')}/10",
                         color='teal').props('outline')

            # Title & Summary
            ui.label(paper.get('summary', 'No summary')).classes(
                'text-lg font-bold leading-tight mt-2 text-slate-900')
            ui.label(paper['title']).classes(
                'text-xs text-slate-400 mt-2 italic')

            # --- HOVER SECTION (Key Findings) ---
            # UPDATED: Hidden by default, Block on group-hover
            # This creates the "opens up on hover" effect
            with ui.column().classes('hidden group-hover:block w-full mt-4 bg-teal-50/50 p-4 rounded border border-teal-100 transition-all'):

                # 1. Findings
                ui.label('Key Findings').classes(
                    'text-xs font-bold text-teal-700 uppercase mb-1')

                findings = paper.get('key_findings', [])
                if findings:
                    for point in findings:
                        ui.label(f"• {point}").classes(
                            'text-sm text-slate-800 ml-2 leading-snug mb-1')
                else:
                    ui.label("No specific data points extracted.").classes(
                        'text-sm text-slate-400 italic')

                ui.separator().classes('my-3 bg-teal-200')

                # 2. Implications
                ui.label('Real World Impact').classes(
                    'text-xs font-bold text-teal-700 uppercase mb-1')

                implications = paper.get('implications', [])
                if isinstance(implications, list):
                    for point in implications:
                        ui.label(f"• {point}").classes(
                            'text-sm text-slate-800 ml-2 leading-snug mb-1')
                else:
                    ui.markdown(str(implications)).classes(
                        'text-sm text-slate-800 leading-relaxed')

            # Footer
            url = paper.get('url') or paper.get('link')

            # FIXED: Link button logic
            if url:
                with ui.row().classes('mt-4 w-full justify-end'):
                    # Explicitly capturing 'url' in lambda to prevent variable overwriting in loops
                    ui.button('Read Source', icon='link',
                              on_click=lambda url=url: ui.open(url, new_tab=True)).props('flat dense color=teal')


def header():
    with ui.header().classes('items-center justify-between bg-white text-slate-800 border-b border-slate-200 elevation-0 h-24'):
        with ui.row().classes('items-center ml-4'):
            # Logo Size: w-20 h-20 (80px)
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
            icon_file = CATEGORY_ICONS.get(hub_name, 'hub')
            with ui.expansion(hub_name, icon=icon_file).classes('w-full text-slate-800 font-bold'):
                for topic in topic_list:
                    # UPDATED: Text color changed to text-teal-600
                    ui.button(topic).props('flat align=left dense').classes(
                        'w-full text-teal-600 font-medium text-sm pl-8 hover:text-teal-800 transition-colors').on_click(lambda t=topic: on_topic_click(t))


@ui.page('/')
def dashboard():
    # --- CSS INJECTION ---
    ui.add_head_html('''
    <style>
        /* Force sidebar icons to be larger (40px) */
        .q-item__section--avatar {
            min-width: 50px !important;
        }
        .q-item__section--avatar .q-icon {
            font-size: 40px !important; 
        }
        .q-item__section--avatar img {
            width: 40px !important;
            height: 40px !important;
        }
    </style>
    ''')

    header()

    # --- LOGIC ---
    def render_feed(papers, title):
        feed_label.set_text(title)
        feed_grid.clear()
        if not papers:
            with feed_grid:
                with ui.column().classes('w-full col-span-2 items-center py-12 text-slate-400'):
                    ui.icon('inbox', size='48px').classes('mb-4')
                    ui.label('No papers found yet.').classes('text-lg')
                    ui.label('Run "nightly_scout.py" to populate your database.').classes(
                        'text-sm italic')
            return
        with feed_grid:
            for paper in papers:
                display_curated_card(feed_grid, paper)

    def load_topic_feed(topic):
        papers = database.get_papers_by_topic(topic)
        render_feed(papers, f'Topic: {topic}')

    def load_home_feed():
        top_papers = database.get_top_rated_papers(limit=12)
        render_feed(top_papers, 'Global Top Hits (Recent)')

    sidebar(on_topic_click=load_topic_feed)

    with ui.column().classes('w-full max-w-5xl mx-auto p-8'):
        ui.label('Deep Search').classes(
            'text-2xl font-bold text-slate-800 mb-4')
        with ui.row().classes('w-full max-w-2xl gap-0'):
            search_input = ui.input(placeholder='Search ArXiv (e.g. "Prosthetics")').props(
                'outlined').classes('flex-grow bg-white')
            search_btn = ui.button(icon='search').props(
                'color=blue-grey-9 size=lg square')

        results_grid = ui.grid(columns=2).classes('w-full gap-4 mt-6')

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

        search_btn.on_click(perform_search)
        search_input.on('keydown.enter', perform_search)

        ui.separator().classes('my-12')

        with ui.row().classes('w-full items-center justify-between mb-4'):
            feed_label = ui.label('Loading...').classes(
                'text-2xl font-bold text-slate-800')
            ui.button('Top Hits', icon='home', on_click=load_home_feed).props(
                'outline color=teal')

        feed_grid = ui.grid(columns=2).classes('w-full gap-4')
        ui.timer(0.1, load_home_feed, once=True)


if __name__ in {"__main__", "__mp_main__"}:
    # Render provides the port in the 'PORT' environment variable
    port = int(os.environ.get("PORT", 8080))

    ui.run(
        title='Skim',
        favicon='assets/logo.png',
        port=port,
        host='0.0.0.0'
    )
