import modal

image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "langchain~=0.0.98", "pymongo[srv]==3.11"
)
