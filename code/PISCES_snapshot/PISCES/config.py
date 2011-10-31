import mapping

#mapping

# configures the default layers and the order they get used (from first to last)
mapping.layer_files = ["gen_1.lyr","gen_2.lyr","gen_3.lyr","gen_4.lyr"]

# set each of the following to True in order to export the corresponding file type, False to disable that type of export.
mapping.export_pdf = True
mapping.export_png = False
mapping.export_mxd = True