if [ -n "$FLAG" ]; then
  echo $FLAG > /ffffffflag
else
  echo "hh";
fi


su -c "node /app/app.js" node