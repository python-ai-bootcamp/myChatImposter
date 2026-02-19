
import inspect
import langchain_openai.chat_models.base as base_module

def inspect_usage_metadata():
    if hasattr(base_module, '_create_usage_metadata'):
        func = getattr(base_module, '_create_usage_metadata')
        print(f"Found _create_usage_metadata in {base_module.__name__}")
        try:
            source = inspect.getsource(func)
            print("--- Source Code ---")
            print(source)
            print("-------------------")
        except Exception as e:
            print(f"Could not get source: {e}")
    else:
        print("_create_usage_metadata not found in langchain_openai.chat_models.base")
        # List items to see if it's named differently
        # print(dir(base_module))

if __name__ == "__main__":
    inspect_usage_metadata()
