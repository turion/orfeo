./main.py -x -gb -lz -ls -lt -lg > output.txt
./main.py -x -t
tar czf $1 global.txt lokal.txt inputs/*.xml {kurs,stunden}plan-ergebnis.pdf output.txt
