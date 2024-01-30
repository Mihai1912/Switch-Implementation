# Implementare Switch (Tema 1 RL)

Cerinte realizate 1 2 3

## Popularea tabelei de comutare

* Pentru inceput am adaugat în tabela de rutare o înregistrare pentru asocierea adresei MAC sursă
  din antetul Ethernet cu portul (interfața) de intrare corespunzător dupa care am verificat daca 
  adresa MAC destinatie este de tip unicasta, in acest caz am verificat daca adresa destinatie se 
  afla in tablea de rutare, iar in lipsa unei intrări pentru adresa MAC destinație,voi trimite 
  cadrul pe toate celelalte porturi disponibile. In cazul in care adresa MAC este de tip multicast 
  voi trimite cadrul pe toate celelalte porturi disponibile.

## Mecanismul de VLAN (Virtual Local Area Networks)

* Pentru implementarea mecanismului de VLAM am modificat codul pentru popularea tabelei de comutare
    prin verificarea tipului protului pe care cadrul a venit (trunk / access). 
  * In cazul in care pachetul vine de pe un port de tip trunk voi verifica pe ce tip de port trebuie
    trimis, iar in functie de tipul portului voi realiza urmatoarele etape:
    * Daca portul pe care trebuie trimis pachetul este trunk nu aduc modificari pachetului primit si
    il trimit pe portul dorit.
    * Daca portul pe care trebuie timirs pachetul este access atunci verific daca VLAN-ul din tagul 
    ```802.1q``` se potriveste cu VLAN-ul portului pe care doresc sa trimit pachetul, in caz afirmativ 
    scot tagul ```802.1q``` si trimit pachetul.
  * In cazul in care pachetul vine de pe un port de tip access voi verifica pe ce tip de port trebuie 
    trimis, iar in functie de tipul portului voi realiza urmatoarele etape:
    * Daca portul pe care trebuie trimis pachetul este trunk voi adauga tagul ```802.1q``` cu VLAN-ul 
    corespunzator portului pe care a venit si il trimit mai devarte.
    * Daca portul pe care trebuie tirimis este access atunci verific VLAN-urile portului de pe care a
    venit si pe care trebuie sa trimti, iar daca acestea sunt egale atunci trimit pachetul, daca nu 
    pachetul se va ignora.

## Algoritmul STP (Spanning Tree Protocol)

* Pentru algoritmul STP implementat de mine am folosit urmatoare structura a pachetului de tip BPDU care
  initial arata in felul urmator:
    ```
    addr_MAC_dest = 01:80:C2:00:00:00
    root_bridge_id = own_bridge_id
    sender_bridge_id = own_bridge_id
    sender_path_cost = 0
    ```
    Fiecare port este inițial configurat în modul blocat (Blocking). În această etapă, fiecare switch 
    consideră că el este "Root Bridge", așa că toate porturile sunt setate să asculte (listen) deoarece 
    sunt desemnate (designated). Următorul pas este determinarea Root Bridge-ului, care se realizează prin 
    consens între toate switch-urile, identificând switch-ul cu cel mai mic ID ca fiind "Root Bridge". 
    În această fază, fiecare switch care se consideră "Root Bridge" trimite periodic un mesaj BPDU 
    (Bridge Protocol Data Unit). La recepționarea unui astfel de mesaj, fiecare switch reacționează în funcție 
    de ID-ul Root Bridge-ului cunoscut. Dacă BPDU-ul primit are un ID mai mic decât cel al "Root Bridge-ului" 
    cunoscut, switch-ul își actualizează configurările porturilor și retransmite BPDU-ul mai departe. Doar 
    porturile considerate "Root" și "Designated" sunt active pentru transmiterea datelor și se află în modul 
    de ascultare (listening).