from nicegui import ui

# --- THEME & LAYOUT ---
# We use a distinct color palette (Blue/Slate) to differentiate it from the News app.


def header():
    with ui.header().classes('items-center justify-between bg-white text-slate-800 border-b border-slate-200 elevation-0'):
        # Logo Area
        with ui.row().classes('items-center ml-4'):
            ui.icon('school', size='32px').classes('text-blue-600 mr-2')
            ui.label('Research Nexus').classes(
                'text-xl font-bold tracking-tight text-slate-900')
            ui.label('v0.1').classes('text-xs text-slate-400 mt-1')

        # Top Nav (Minimalist)
        with ui.row().classes('mr-6 gap-6'):
            ui.link(
                'Dashboard', '/').classes('text-slate-600 no-underline hover:text-blue-600 font-medium')
            ui.link('Saved Papers', '/saved').classes(
                'text-slate-600 no-underline hover:text-blue-600 font-medium')
            ui.button(icon='settings').props('flat round dense color=slate')


def sidebar():
    """A left drawer for filtering specific academic disciplines."""
    with ui.left_drawer(value=True).classes('bg-slate-50 border-r border-slate-200 p-4'):
        ui.label('Disciplines').classes(
            'text-xs font-bold text-slate-400 uppercase mb-4 tracking-wider')

        # Navigation / Filters
        # We can eventually link these to filter the search results
        with ui.column().classes('gap-2 w-full'):
            ui.button('All Fields', icon='apps').props(
                'flat align=left').classes('w-full text-slate-700')
            ui.button('Electrical Eng.', icon='bolt').props(
                'flat align=left').classes('w-full text-slate-700')
            ui.button('Bionics & Bio-tech', icon='accessibility').props(
                'flat align=left').classes('w-full text-slate-700')
            ui.button('Comp Sci', icon='terminal').props(
                'flat align=left').classes('w-full text-slate-700')
            ui.button('Mathematics', icon='functions').props(
                'flat align=left').classes('w-full text-slate-700')

# --- PAGE CONTENT ---


@ui.page('/')
def dashboard():
    header()
    sidebar()

    with ui.column().classes('w-full max-w-5xl mx-auto p-8'):
        # Hero Section / Search
        with ui.column().classes('w-full items-center py-12'):
            ui.label('Accelerate your discovery.').classes(
                'text-4xl font-extrabold text-slate-800 mb-2')
            ui.label('Search millions of papers from ArXiv, IEEE, and PubMed.').classes(
                'text-slate-500 mb-8')

            # Main Search Bar
            with ui.row().classes('w-full max-w-2xl shadow-sm border border-slate-200 rounded-lg bg-white p-1'):
                search_input = ui.input(placeholder='Search for keywords, DOIs, or authors...').props(
                    'borderless w-full').classes('flex-grow px-4')
                ui.button(icon='search').props(
                    'flat color=blue').classes('rounded-r-lg')

        ui.separator()

        # "Recent Feeds" Section (Placeholder for API Data)
        ui.label('Latest in Electrical Engineering').classes(
            'text-xl font-bold text-slate-800 mt-8 mb-4')

        # Grid of Paper Cards
        with ui.grid(columns=2).classes('w-full gap-4'):
            for i in range(4):  # Just creating 4 fake cards for visual test
                with ui.card().classes('w-full hover:shadow-md transition-shadow cursor-pointer'):
                    with ui.row().classes('justify-between w-full'):
                        ui.label('IEEE Transaction on Robotics').classes(
                            'text-xs text-blue-600 font-bold')
                        ui.label('Oct 24, 2025').classes(
                            'text-xs text-slate-400')

                    ui.label('Soft Robotic Manipulators for Minimally Invasive Surgery').classes(
                        'text-lg font-bold leading-tight mt-2 text-slate-800')
                    ui.label('Authors: J. Smith, A. Doe et al.').classes(
                        'text-sm text-slate-500 mt-1')

                    with ui.row().classes('mt-4 gap-2'):
                        ui.chip('Robotics', icon='memory').props(
                            'dense outline color=slate')
                        ui.chip('Medical', icon='medical_services').props(
                            'dense outline color=slate')


@ui.page('/saved')
def saved_papers():
    header()
    sidebar()
    with ui.column().classes('p-8'):
        ui.label('Your Library').classes('text-3xl font-bold text-slate-800')
        ui.label('No papers saved yet.').classes('text-slate-500 mt-4')


# --- RUN ---
ui.run(title='Research Nexus', favicon='🎓', native=False)
