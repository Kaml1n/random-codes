#!/usr/bin/env python
 
import whois
import sys
 
file=open('domain_list.txt').read()
 
lines = file.split('\n')
 
for line in lines:
    sys.stdout.write(line)
    try:
        domain = whois.query(line)
    except:
        break
    try:   
        date = domain.creation_date
        sys.stdout.write(", date of registration: "+date.strftime('%d/%m/%Y'))
    except:
        pass
    try:
        reg = domain.registrar
        sys.stdout.write(", by: "+domain.registrar)
    except:
        pass
    sys.stdout.write("\n")
