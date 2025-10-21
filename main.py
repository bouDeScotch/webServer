from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8000

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Mon joli site</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            min-height: 100vh;
        }
        header {
            width: 100%;
            background-color: #343a40;
            color: white;
            padding: 1em;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        main {
            padding: 2em;
            max-width: 800px;
            text-align: center;
        }
        h1 {
            color: #495057;
        }
        p {
            font-size: 1.2em;
            color: #6c757d;
        }
        button {
            background-color: #007bff;
            border: none;
            color: white;
            padding: 0.8em 1.2em;
            font-size: 1em;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #0056b3;
        }
        footer {
            margin-top: auto;
            padding: 1em;
            width: 100%;
            text-align: center;
            background-color: #f1f3f5;
            color: #495057;
        }
    </style>
</head>
<body>
    <header>
        <h1>Bienvenue sur mon site Python !</h1>
    </header>
    <main>
        <p>Ce site est servi directement depuis un fichier Python sur le port 8000.</p>
        <p>Amuse-toi bien et clique sur le bouton ci-dessous :</p>
        <button onclick="alert('Bravo ! Tu as cliqué !')">Clique-moi</button>
    </main>
    <footer>
        &copy; 2025 Florian
    </footer>
</body>
</html>
"""

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode('utf-8'))

def run():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"Serveur lancé sur http://localhost:{PORT}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
