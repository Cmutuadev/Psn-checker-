with open('main.py', 'r') as f:
    content = f.read()

# Fix msh import
old_msh = """from mass_gates.msh import (
    router as msh_router, msh_stop_handler, msh_result_handler
)"""
new_msh = "from mass_gates.msh import router as msh_router"

# Fix mst import
old_mst = """from mass_gates.mst import (
    router as mst_router, mst_stop_handler, mst_result_handler, mst_command
)"""
new_mst = "from mass_gates.mst import router as mst_router, mst_command"

content = content.replace(old_msh, new_msh)
content = content.replace(old_mst, new_mst)

# Fix callback registrations
content = content.replace('dp.callback_query.register(msh_stop_handler, F.data.startswith("msh_stop_"))', '# dp.callback_query.register(msh_stop_handler, F.data.startswith("msh_stop_"))')
content = content.replace('dp.callback_query.register(msh_result_handler, F.data.startswith("msh_result_"))', '# dp.callback_query.register(msh_result_handler, F.data.startswith("msh_result_"))')
content = content.replace('dp.callback_query.register(mst_stop_handler, F.data.startswith("mst_stop_"))', '# dp.callback_query.register(mst_stop_handler, F.data.startswith("mst_stop_"))')
content = content.replace('dp.callback_query.register(mst_result_handler, F.data.startswith("mst_result_"))', '# dp.callback_query.register(mst_result_handler, F.data.startswith("mst_result_"))')

with open('main.py', 'w') as f:
    f.write(content)

print("✅ main.py imports fixed!")
