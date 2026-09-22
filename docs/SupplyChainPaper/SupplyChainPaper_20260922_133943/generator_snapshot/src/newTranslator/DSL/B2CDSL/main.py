from textx import export_model
from textx.metamodel import metamodel_from_file

mm = metamodel_from_file('./b2cdsl/b2c.tx')

export_model(mm.metamodel.model, "metamodel.dot")


