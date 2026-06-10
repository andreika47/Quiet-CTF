require('http').createServer((a,b)=>b.writeHead(200,{'content-type':'text/html',link:`<${unescape(a.url)}>;rel=preload;as=fetch`})+b.end(`<body onload=fetch('${a.headers.cookie}')>`)).listen(8080)
