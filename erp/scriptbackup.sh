#!/bin/bash

while true; do
    # Obtenir le jour de la semaine et l'heure actuelle
    current_day=$(date +%u)  # 1 = lundi, 2 = mardi, ..., 7 = dimanche
    current_hour=$(date +%H)  # Heure en format 24h (00 à 23)

    # Vérifier si c'est vendredi (5) ou samedi (6)
    if [[ "$current_day" -eq 5 || "$current_day" -eq 6 ]]; then
        echo "C'est vendredi ou samedi. Le script ne s'exécute pas."
        next_run=$(date -d "next sunday 08:00" +%s)  # Attendre jusqu'à dimanche matin à 8h
        now=$(date +%s)
        sleep $((next_run - now))

    # Vérifier si l'heure est entre 8h et 17h du lundi au jeudi
    elif [[ "$current_hour" -ge 8 && "$current_hour" -lt 17 ]]; then
        # Exécuter le script Python
        /usr/bin/python3 /root/Erps/erpfinal/erp/backup.py  # Exécuter votre script Python
        
        # Attendre 3 heures avant de réexécuter
        sleep 3h
    else
        # Attendre jusqu'à 8h le lendemain matin
        echo "Il est en dehors des heures de travail. Attente jusqu'à demain matin à 8h..."
        next_run=$(date -d "tomorrow 08:00" +%s)
        now=$(date +%s)
        sleep $((next_run - now))
    fi
done


