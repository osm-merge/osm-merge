#!/bin/bash

for i in *.png; do
    name="small-${i}"
    pngtopnm $i | pamscale  -reduce 4 | pamtopng > ${name}
done

