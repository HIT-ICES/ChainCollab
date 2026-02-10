# emf-random instantiator (Java 17 fix)

`instantiator-fatjar.jar` is an Eclipse “jar-in-jar” runnable JAR (it contains its dependencies as nested `*.jar` files). On **Java 17** it fails to load those nested JARs and crashes with:

`java.lang.NoClassDefFoundError: org/apache/commons/cli/ParseException`

## Recommended

Use the provided wrapper, which repacks a normal “uber JAR” once and then runs it:

```bash
cd /home/shenxz-lab/code/ChainCollab/src/newTranslator/MDAcheck/emf-random
./run_instantiator.sh -m /home/shenxz-lab/code/ChainCollab/src/newTranslator/MDAcheck/b2c.ecore -n 100 -s 1000 -e 12345
```

This creates `instantiator-uber.jar` (generated) and executes it via `java -jar`.

## Manual repack

```bash
./repack_instantiator_uberjar.sh
java -jar instantiator-uber.jar <args>
```

