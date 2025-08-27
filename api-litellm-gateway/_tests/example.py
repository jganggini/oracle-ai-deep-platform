from langchain_openai import ChatOpenAI
import time

# Local Gateway API
print("=" * 50)
print("Gateway API: http://localhost:4000/litellm/oci/v1")
print("=" * 50)

llm_local = ChatOpenAI(
    model="xai.grok-4",
    api_key="oci-***",
    base_url="http://localhost:4000/litellm/oci/v1",
    temperature=0,
)

start_loc = time.perf_counter()
resp_loc = llm_local.invoke("Hola, respóndeme en español.")
elapsed_loc_ms = (time.perf_counter() - start_loc) * 1000
print(resp_loc.content if hasattr(resp_loc, "content") else resp_loc)
print(f"Tiempo (local): {elapsed_loc_ms:.2f} ms")





