from django import forms
from . import nomenclature_ahi as n


class ReleveAHIForm(forms.Form):
    attendu = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, adultes, reference, sortie, releve, attendu, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['attendu'] = attendu
        self.reference = reference
        self.adultes = []
        self.menage = []
        self.fields['adresse_logement'] = forms.CharField(label='Adresse du logement fourni', max_length=500, required=False)
        self.initial['adresse_logement'] = releve.get('adresse_logement', '')
        self.menage.append('adresse_logement')
        for adulte in adultes:
            personne = adulte['personne']
            identifiant = str(personne.pk)
            champs = []
            for code, (label, choix) in n.ADULTE.items():
                nom = f'{code}_{identifiant}'
                self.fields[nom] = forms.ChoiceField(label=label, choices=[('', 'Non renseigné'), *choix.items()], required=False)
                self.initial[nom] = releve.get('adultes', {}).get(identifiant, {}).get(code, '')
                champs.append(nom)
            for code, (label, choix) in n.CHOIX_MULTIPLES.items():
                nom = f'{code}_{identifiant}'
                self.fields[nom] = forms.MultipleChoiceField(
                    label=label, choices=choix.items(), required=False, widget=forms.CheckboxSelectMultiple,
                )
                self.initial[nom] = releve.get('adultes', {}).get(identifiant, {}).get(code, [])
                champs.append(nom)
            self.adultes.append((personne, champs))
        for code, (label, choix) in n.MENAGE.items():
            if (code == 'sortie' and sortie) or (code != 'sortie' and reference):
                self.fields[code] = forms.ChoiceField(label=label, choices=[('', 'Non renseigné'), *choix.items()], required=False)
                meme_reference = reference and releve.get('reference') == str(reference.pk)
                self.initial[code] = releve.get(code, '') if code == 'sortie' or meme_reference else ''
                self.menage.append(code)
        if sortie:
            self.fields['adresse_sortie'] = forms.CharField(label='Adresse de correspondance à la sortie', max_length=500, required=False)
            self.fields['qualifications'] = forms.MultipleChoiceField(
                label='Précisions sur la sortie', choices=n.QUALIFICATIONS_SORTIE.items(), required=False,
                widget=forms.CheckboxSelectMultiple,
            )
            for nom in ('adresse_sortie', 'qualifications'):
                self.initial[nom] = releve.get(nom)
                self.menage.append(nom)

    def groupes(self):
        return [(personne, [self[nom] for nom in noms]) for personne, noms in self.adultes]

    def champs_menage(self):
        return [self[nom] for nom in self.menage]

    def releve(self):
        donnees = {nom: self.cleaned_data[nom] for nom in self.menage if self.cleaned_data[nom]}
        if {'droits', 'couverture'} & donnees.keys():
            donnees['reference'] = str(self.reference.pk)
        donnees['adultes'] = {}
        for personne, noms in self.adultes:
            valeurs = {nom.split('_', 1)[0]: self.cleaned_data[nom] for nom in noms if self.cleaned_data[nom]}
            if valeurs:
                donnees['adultes'][str(personne.pk)] = valeurs
        return donnees
