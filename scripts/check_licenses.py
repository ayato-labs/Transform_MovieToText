import importlib.metadata
for d in importlib.metadata.distributions():
    name = d.metadata.get('Name', 'Unknown')
    license = d.metadata.get('License', 'Unknown')
    # Sometimes license is in License-Expression or Classifiers
    if not license or license == 'UNKNOWN':
        classifiers = d.metadata.get_all('Classifier')
        if classifiers:
            license_classifiers = [c.split('::')[-1].strip() for c in classifiers if 'License' in c]
            if license_classifiers:
                license = ', '.join(license_classifiers)
    
    # Check License-Expression if available (PEP 639)
    lexp = d.metadata.get('License-Expression')
    if lexp:
        license = lexp
        
    print(f"{name}: {license}")
