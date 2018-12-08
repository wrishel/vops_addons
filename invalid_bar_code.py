
lines = 0
badc = 0
failc = 0
with open('/Users/Wes/NotForTheCloud/vops/180909/newnewdetails.csv') as inf:
    for l in inf.readlines():
        lines += 1
        try:
            barc = l.split(',')[1]
        except Exception as e:
            failc += 1
            print l
        else:
            if len(barc) != 14 or not barc.isdigit():
                badc += 1

print badc, failc, lines, float(badc)/lines
