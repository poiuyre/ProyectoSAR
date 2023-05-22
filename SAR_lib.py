import json
from nltk.stem.snowball import SnowballStemmer
import os
import re
import sys
import math
from pathlib import Path
from typing import Optional, List, Union, Dict
import pickle
from distutils import filelist

class SAR_Indexer:
    """
    Prototipo de la clase para realizar la indexacion y la recuperacion de artículos de Wikipedia
        
        Preparada para todas las ampliaciones:
          parentesis + multiples indices + posicionales + stemming + permuterm

    Se deben completar los metodos que se indica.
    Se pueden añadir nuevas variables y nuevos metodos
    Los metodos que se añadan se deberan documentar en el codigo y explicar en la memoria
    """

    # lista de campos, el booleano indica si se debe tokenizar el campo
    # NECESARIO PARA LA AMPLIACION MULTIFIELD
    fields = [
        ("all", True), ("title", True), ("summary", True), ("section-name", True),('url', False)] #
    
    def_field = 'all'
    PAR_MARK = '%'
    # numero maximo de documento a mostrar cuando self.show_all es False
    SHOW_MAX = 10

    all_atribs = ['urls', 'index', 'sindex', 'ptindex', 'docs', 'weight', 'articles',
                  'tokenizer', 'stemmer', 'show_all', 'use_stemming']

    def __init__(self):
        """
        Constructor de la classe SAR_Indexer.
        NECESARIO PARA LA VERSION MINIMA

        Incluye todas las variables necesaria para todas las ampliaciones.
        Puedes añadir más variables si las necesitas 

        """
        self.urls = set() # hash para las urls procesadas,
        self.index =  {
            'all': {},
            'title': {},
            'summary': {},
            'section-name': {},
            'url': {}
        } # hash para el indice invertido de terminos --> clave: termino, valor: posting list
        self.sindex = {
            'all': {},
            'title': {},
            'summary': {},
            'section-name': {},
            'url': {}
        } # hash para el indice invertido de stems --> clave: stem, valor: lista con los terminos que tienen ese stem
        self.ptindex = {
            'all': {},
            'title': {},
            'summary': {},
            'section-name': {},
            
        } # hash para el indice permuterm.
        self.docs = {} # diccionario de terminos --> clave: entero(docid),  valor: ruta del fichero.
        self.weight = {} # hash de terminos para el pesado, ranking de resultados.
        self.articles = {} # hash de articulos --> clave entero (artid), valor: la info necesaria para diferencia los artículos dentro de su fichero
        self.tokenizer = re.compile("\W+") # expresion regular para hacer la tokenizacion
        self.stemmer = SnowballStemmer('spanish') # stemmer en castellano
        self.show_all = False # valor por defecto, se cambia con self.set_showall()
        self.show_snippet = False # valor por defecto, se cambia con self.set_snippet()
        self.use_stemming = False # valor por defecto, se cambia con self.set_stemming()
        self.use_ranking = False  # valor por defecto, se cambia con self.set_ranking()
        
        self.docid = 0
        self.artid = 0
        self.ntokens = 0



    ###############################
    ###                         ###
    ###      CONFIGURACION      ###
    ###                         ###
    ###############################


    def set_showall(self, v:bool):
        """

        Cambia el modo de mostrar los resultados.
        
        input: "v" booleano.

        UTIL PARA TODAS LAS VERSIONES

        si self.show_all es True se mostraran todos los resultados el lugar de un maximo de self.SHOW_MAX, no aplicable a la opcion -C

        """
        self.show_all = v


    def set_snippet(self, v:bool):
        """

        Cambia el modo de mostrar snippet.
        
        input: "v" booleano.

        UTIL PARA TODAS LAS VERSIONES

        si self.show_snippet es True se mostrara un snippet de cada noticia, no aplicable a la opcion -C

        """
        self.show_snippet = v


    def set_stemming(self, v:bool):
        """

        Cambia el modo de stemming por defecto.
        
        input: "v" booleano.

        UTIL PARA LA VERSION CON STEMMING

        si self.use_stemming es True las consultas se resolveran aplicando stemming por defecto.

        """
        self.use_stemming = v



    #############################################
    ###                                       ###
    ###      CARGA Y GUARDADO DEL INDICE      ###
    ###                                       ###
    #############################################


    def save_info(self, filename:str):
        """
        Guarda la información del índice en un fichero en formato binario
        
        """
        info = [self.all_atribs] + [getattr(self, atr) for atr in self.all_atribs]
        with open(filename, 'wb') as fh:
            pickle.dump(info, fh)

    def load_info(self, filename:str):
        """
        Carga la información del índice desde un fichero en formato binario
        
        """
        #info = [self.all_atribs] + [getattr(self, atr) for atr in self.all_atribs]
        with open(filename, 'rb') as fh:
            info = pickle.load(fh)
        atrs = info[0]
        for name, val in zip(atrs, info[1:]):
            setattr(self, name, val)

    ###############################
    ###                         ###
    ###   PARTE 1: INDEXACION   ###
    ###                         ###
    ###############################

    def already_in_index(self, articles:Dict) -> bool:
        """

        Args:
            articles (Dict): diccionario con la información de un artículo

        Returns:
            bool: True si el artículo ya está indexado, False en caso contrario
        """
        return articles['url'] in self.urls


    def index_dir(self, root:str, **args):
        """
        
        Recorre recursivamente el directorio o fichero "root" 
        NECESARIO PARA TODAS LAS VERSIONES
        
        Recorre recursivamente el directorio "root"  y indexa su contenido
        los argumentos adicionales "**args" solo son necesarios para las funcionalidades ampliadas

        """
        self.multifield = args['multifield']
        self.positional = args['positional']
        self.stemming = args['stem']
        self.permuterm = args['permuterm']

        file_or_dir = Path(root)
        
        if file_or_dir.is_file():
            # is a file
            self.index_file(root)
        elif file_or_dir.is_dir():
            # is a directory
            for d, _, files in os.walk(root):
                for filename in files:
                    if filename.endswith('.json'):
                        fullname = os.path.join(d, filename)
                        self.index_file(fullname)
        else:
            print(f"ERROR:{root} is not a file nor directory!", file=sys.stderr)
            sys.exit(-1)

        ##########################################
        ## COMPLETAR PARA FUNCIONALIDADES EXTRA ##
        ##########################################
        if self.stemming:
            self.make_stemming()
        
    def parse_articles(self, raw_line:str) -> Dict[str, str]:
        """
        Crea un diccionario a partir de una linea que representa un artículo del crawler

        Args:
            raw_line: una linea del fichero generado por el crawler

        Returns:
            Dict[str, str]: claves: 'url', 'title', 'summary', 'all', 'section-name'
        """
        
        articles = json.loads(raw_line)
        sec_names = []
        txt_secs = ''
        for sec in articles['sections']:
            txt_secs += sec['name'] + '\n' + sec['text'] + '\n'
            txt_secs += '\n'.join(subsec['name'] + '\n' + subsec['text'] + '\n' for subsec in sec['subsections']) + '\n\n'
            sec_names.append(sec['name'])
            sec_names.extend(subsec['name'] for subsec in sec['subsections'])
        articles.pop('sections') # no la necesitamos 
        articles['all'] = articles['title'] + '\n\n' + articles['summary'] + '\n\n' + txt_secs
        articles['section-name'] = '\n'.join(sec_names)

        return articles
                
    
    def index_file(self, filename:str):
        """

        Indexa el contenido de un fichero.
        pytho
        input: "filename" es el nombre de un fichero generado por el Crawler cada línea es un objeto json
            con la información de un artículo de la Wikipedia

        NECESARIO PARA TODAS LAS VERSIONES

        dependiendo del valor de self.multifield y self.positional se debe ampliar el indexado


        """

        self.docs[self.docid] = filename   
        for i, line in enumerate(open(filename)):
            
            j = self.parse_articles(line)
            
            url = j['url']
            if any(url == article[2] for article in self.articles.values()):
                # Hay al menos una coincidencia de URL en self.articles
                pass
            else:
                # No hay ninguna coincidencia de URL en self.articles
                self.articles[self.artid] = (self.docid, i, url)        

            if not self.multifield:
                tokens = self.tokenize(j['all'])
                for t in tokens:
                    #print(self.index['all'][t]['docid'])
                    if not self.index['all'].get(t):    #si no hay ninguna entrada de ese token
                        
                        
                        self.index['all'][t] = {'docid': [self.docid], 'artid': [self.artid]}# se añade la referencia al documento y articulo al que pertenece el token
                        self.ntokens = self.ntokens + 1 # numero de tokens
                        
                    else:                 #si hay alguna entrada de ese token
                        self.index['all'][t]["artid"].append(self.artid)
                        self.index['all'][t]["docid"].append(self.docid)
                self.artid = self.artid + 1

            else:
                fields = ['all', 'title', 'summary', 'section-name', 'url']

                for field in fields:
                    if field != 'url': # si el campo no es url tokenizamos
                        tokens = self.tokenize(j[field])
                        for t in tokens:
                            
                            if self.index[field].get(t) == None:
                                
                                self.index[field][t] = {'docid': [self.docid], 'artid': [self.artid]}
                                self.ntokens = self.ntokens + 1 
                            else:
                               self.index[field][t]["artid"].append(self.artid)
                               self.index[field][t]["docid"].append(self.docid)
                    else:

                        aux = j['url'].splitlines() # partimos el j['url'] en lineas para comprobar que no estan ya en index igual que al principio en articles
                        
                        for t in aux:
                            if self.index['url'].get(t) == None:
                                
                                self.index['url'][t] = {'docid': [self.docid], 'artid': [self.artid]}
                                self.ntokens = self.ntokens + 1 
                            else:
                                
                                self.index['url'][t]["artid"].append(self.artid)
                                self.index['url'][t]["docid"].append(self.docid)
                                
            
                self.artid = self.artid + 1
            
            self.docid = self.docid + 1 # contador de documentos

        #
        # 
        # En la version basica solo se debe indexar el contenido "articles"
        #
        #
        #
        #################
        ### COMPLETAR ###
        #################



    def set_stemming(self, v:bool):
        """

        Cambia el modo de stemming por defecto.
        
        input: "v" booleano.

        UTIL PARA LA VERSION CON STEMMING

        si self.use_stemming es True las consultas se resolveran aplicando stemming por defecto.

        """
        self.use_stemming = v


    def tokenize(self, text:str):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Tokeniza la cadena "texto" eliminando simbolos no alfanumericos y dividientola por espacios.
        Puedes utilizar la expresion regular 'self.tokenizer'.

        params: 'text': texto a tokenizar

        return: lista de tokens

        """
        return self.tokenizer.sub(' ', text.lower()).split()


    def make_stemming(self):
        """

        Crea el indice de stemming (self.sindex) para los terminos de todos los indices.

        NECESARIO PARA LA AMPLIACION DE STEMMING.

        "self.stemmer.stem(token) devuelve el stem del token"


        """

        if self.multifield:
            multifield = ['all','title','summary','section-name', 'url']
            
        else:
            multifield = ['all']
        for field in multifield:
            if field != 'url':
                for token in self.index[field].keys():
                    steam_token = self.stemmer.stem(token)
                    if steam_token not in self.sindex[field]:
                        
                        self.sindex[field][steam_token] = [token]
                    else:
                        
                        if token not in self.sindex[field][steam_token]:
                            self.sindex[field][steam_token] += [token]
            else:
                for token in self.index[field].keys():
                    if token not in self.sindex[field]:
                        
                        self.sindex[field][token] = [token]
        

        
        ####################################################
        ## COMPLETAR PARA FUNCIONALIDAD EXTRA DE STEMMING ##
        ####################################################


    
    def make_permuterm(self):
        """

        Crea el indice permuterm (self.ptindex) para los terminos de todos los indices.

        NECESARIO PARA LA AMPLIACION DE PERMUTERM


        """
        pass
        ####################################################
        ## COMPLETAR PARA FUNCIONALIDAD EXTRA DE STEMMING ##
        ####################################################




    def show_stats(self):
        """
        NECESARIO PARA TODAS LAS VERSIONES
        
        Muestra estadisticas de los indices
        
        """
        print("=" * 40)
        print("Number of indexed files:", len(self.docs))
        print("-" * 40)
        print("Number of indexed articles:", len(self.articles)) #
        print("-" * 40)
        print('TOKENS:', self.ntokens)
        for field, tok in self.fields:
            if (self.multifield or field == "all"):
                print("\t# of tokens in '{}': {}".format(field, len(self.index[field])))
        if (self.permuterm):
            print("-" * 40)
            print('PERMUTERMS:')
            for field, tok in self.fields:
                if (self.multifield or field == "all"):
                    print("\t# of tokens in '{}': {}".format(field, len(self.ptindex[field])))
        if (self.stemming):
            print("-" * 40)
            print('STEMS:')
            for field, tok in self.fields:
                if (self.multifield or field == "all"):
                    print("\t# of tokens in '{}': {}".format(field, len(self.sindex[field])))
        print("-" * 40)
        if (self.positional):
            print('Positional queries are allowed.')
        else:    
            print('Positional queries are NOT allowed.')
        print("=" * 40)
        
        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################

        



    #################################
    ###                           ###
    ###   PARTE 2: RECUPERACION   ###
    ###                           ###
    #################################

    ###################################
    ###                             ###
    ###   PARTE 2.1: RECUPERACION   ###
    ###                             ###
    ###################################
    def get_field(self, query):
        """
        Separar campo para la busqueda de query

        param:  "query": cadena con el fragmeto de la query

        return: campo de la busqueda, fragmento de la query

        """
        field = 'all'

        if query.startswith(('all:','title', 'summary', 'section-name', 'url')):
            field, query = query[:query.index(':')], query[query.index(':')+1:]

        return field, query
    


    def solve_query(self, query:str, prev:Dict={}):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Resuelve una query.
        Debe realizar el parsing de consulta que sera mas o menos complicado en funcion de la ampliacion que se implementen


        param:  "query": cadena con la query
                "prev": incluido por si se quiere hacer una version recursiva. No es necesario utilizarlo.


        return: posting list con el resultado de la query

        """
        # Si no hay nada en la query, se devuelve la lista vacía
        if query is None or len(query) == 0:
            return []
        
        # Preproceso de la query si es un string. La convertimos en una lista de elementos (incluidos operaciones, parentesis y posicionales)
        if isinstance(query, str): queryList = self.prepare_query_list(query)
        else: queryList = query
        
        # Caso base si solo hay un elemento para el que resolver la consulta
        self.multifield = True
        if len(queryList) == 1:
            element = queryList[0]
            # Si el indice es multicampo, guardamos el campo donde se buscara. Si no lo es, buscamos en 'all'
            if self.multifield: field, element = self.get_field(element)
            else: field, element = 'all', query
            # Si esta entre parentesis, los quitamos y llamamos a solve_query de la consulta interior
            if element.startswith('(') and element.endswith(')'):
                element = element[1:len(element)-1] 
                return self.solve_query(element)
            return self.get_posting(element, field)
            
        # Caso general: Si hay más de un elemento en la búsqueda        
        if len(queryList) > 1:
            opIndex = len(queryList) - 2
            operation = queryList[opIndex]
            beforeOp = queryList[0:opIndex]
            afterOp = queryList[opIndex + 1]
            # Llamadas recursivas en función de la operación a realizar
            if operation == 'or':
                return self.or_posting(self.solve_query(beforeOp), self.solve_query(afterOp))
            elif operation == 'and':
                return self.and_posting(self.solve_query(beforeOp), self.solve_query(afterOp))
            elif operation == 'not':
                # Si la operación es not, consultamos si hay otra operación que la precede y resolvemos
                if opIndex > 0: opIndex -= 1; operation = queryList[opIndex] # Si not es el primer elemento de la lista, no decrementamos el puntero
                else: return self.reverse_posting(self.solve_query(afterOp)) # Si lo es, resolvemos el not

                beforeOp = queryList[0:opIndex]
                if operation == 'or':
                    return self.or_posting(self.solve_query(beforeOp), 
                        self.reverse_posting(self.solve_query(afterOp)))
                elif operation == 'and':
                    return self.and_posting(self.solve_query(beforeOp), 
                        self.reverse_posting(self.solve_query(afterOp)))

        

        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################

        
    def prepare_query_list(self, query):
        """
        Convierte una query en una lista de elementos, apartando los elementos entre parentesis y comillas
        Tambien añadimos and donde sea necesario
        Debe realizar el parsing de consulta que sera mas o menos complicado en funcion de la ampliacion que se implementen
        param:  "query": cadena con la query
        return: lista con los elemetos mas superficiales de la query
        """

        openPar = [m.start() for m in re.finditer(r'\(',query)]
        closePar = [m.start() for m in re.finditer(r'\)',query)]
        
        # Conteo de parentesis
        ini = []; fin = []; closed = 0
        for index in sorted(openPar + closePar):
            if closed == 0: ini.append(index)
            if index in openPar:
                closed += 1
            else:
                closed -= 1
            if closed == 0: fin.append(index)

        # Separar por parentesis mas externos
        if len(ini) > 0:
            if query[:ini[0]] != '':
                parenList = [query[:ini[0]].strip()]
            else: parenList = []
            for index,element in enumerate(ini):
                parenList.append(query[ini[index]:fin[index] + 1].strip())
                if index + 1 < len(ini):
                    parenList.append(query[fin[index] + 1: ini[index + 1]].strip())
            if len(query) > fin[len(fin) - 1] + 1:
                parenList.append(query[fin[len(fin) - 1] + 1:].strip())
        else: parenList = [query]
        # Separar por comillas
        comList = []
        for element in parenList:
            if '\"' in element and '(' not in element:
                comi = [m.start() for m in re.finditer(r'\"',element)]
                if element[:comi[0]] != '': elementList = [element[:comi[0]].strip()]
                else: elementList = []
                for index, c in enumerate(comi):
                    if index % 2 == 0:
                        elementList.append(element[comi[index]:comi[index + 1] + 1])
                    elif index < len(comi) - 1:
                        elementList.append(element[comi[index] + 1:comi[index + 1]].strip())
                if len(element) > comi[len(comi) - 1] + 1:
                    elementList.append(element[comi[len(comi) - 1] + 1:].strip())
                
                for e in elementList: comList.append(e)
            else:
                comList.append(element)

        # Tokenizar aquellos elementos no dependientes de comillas ni parentesis
        spcList = []
        for element in comList:
            if '\"' not in element and '(' not in element:
                elementList = element.split(' ')
                for e in elementList: spcList.append(e.strip())
            else:
                spcList.append(element)

        # Insertar ands donde haga falta (y unificar en un elemento busqueda posicional y su field)
        queryFinal = []
        needAnd = False # Booleano para saber si hace falta un and
        for ind, word in enumerate(spcList):
            word = word.strip()
            if word in ['all:','title', 'summary', 'section-name', 'url'] and spcList[ind+1].startswith('"'):
                spcList[ind+1] = word + spcList[ind+1]
                if needAnd:
                    queryFinal.append('and')
                    needAnd = False
            elif not needAnd:
                queryFinal.append(word)
                needAnd = True
                if word == 'not':
                    needAnd = False
            elif needAnd:
                if word in ['or','and']:
                    queryFinal.append(word)
                    needAnd = False
                else:
                    queryFinal.append('and')
                    queryFinal.append(word)
                    if word == 'not':
                        needAnd = False

        return queryFinal    
        
        
        
        



    def get_posting(self, term:str, field:Optional[str]=None):
        """

        Devuelve la posting list asociada a un termino. 
        Dependiendo de las ampliaciones implementadas "get_posting" puede llamar a:
            - self.get_positionals: para la ampliacion de posicionales
            - self.get_permuterm: para la ampliacion de permuterms
            - self.get_stemming: para la amplaicion de stemming


        param:  "term": termino del que se debe recuperar la posting list.
                "field": campo sobre el que se debe recuperar la posting list, solo necesario si se hace la ampliacion de multiples indices

        return: posting list
        
        NECESARIO PARA TODAS LAS VERSIONES

        """
        # Llamada al get que corresponde según los parámetros indicados
        solution = []
        self.permuterm = False
        self.positional = False
        self.stemming = False
        if self.permuterm and ('*' in term or '?' in term):
            solution =  self.get_permuterm(term, field)
        elif self.positional:
            if '\"' in term:
                term = term.replace('\"','')
                solution = self.get_positionals(term.split(' '), field)
            elif self.stemming and self.use_stemming:
                solution =  self.get_stemming(term, field)
            else:
                solution = self.get_positionals([term], field)
        elif self.stemming and self.use_stemming:
            solution =  self.get_stemming(term, field)
        else:
            solution =  self.index[field][term]

        return solution
        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################
        



    def get_positionals(self, terms:str, index):
        """

        Devuelve la posting list asociada a una secuencia de terminos consecutivos.
        NECESARIO PARA LA AMPLIACION DE POSICIONALES

        param:  "terms": lista con los terminos consecutivos para recuperar la posting list.
                "field": campo sobre el que se debe recuperar la posting list, solo necesario se se hace la ampliacion de multiples indices

        return: posting list

        """
        pass
        ########################################################
        ## COMPLETAR PARA FUNCIONALIDAD EXTRA DE POSICIONALES ##
        ########################################################


    def get_stemming(self, term:str, field: Optional[str]=None):
        """

        Devuelve la posting list asociada al stem de un termino.
        NECESARIO PARA LA AMPLIACION DE STEMMING

        param:  "term": termino para recuperar la posting list de su stem.
                "field": campo sobre el que se debe recuperar la posting list, solo necesario se se hace la ampliacion de multiples indices

        return: posting list

        """
        
        stem = self.stemmer.stem(term)

        pos_list = []
        if (stem in self.sindex[field]):
            for token in self.sindex[field][stem]:
                pos_list = self.or_posting(pos_list, list(self.index[field][token].keys()))
        return pos_list

        ####################################################
        ## COMPLETAR PARA FUNCIONALIDAD EXTRA DE STEMMING ##
        ####################################################

    def get_permuterm(self, term:str, field:Optional[str]=None):
        """

        Devuelve la posting list asociada a un termino utilizando el indice permuterm.
        NECESARIO PARA LA AMPLIACION DE PERMUTERM

        param:  "term": termino para recuperar la posting list, "term" incluye un comodin (* o ?).
                "field": campo sobre el que se debe recuperar la posting list, solo necesario se se hace la ampliacion de multiples indices

        return: posting list

        """

        ##################################################
        ## COMPLETAR PARA FUNCIONALIDAD EXTRA PERMUTERM ##
        ##################################################
        pass



    def reverse_posting(self, p:list):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Devuelve una posting list con todas las noticias excepto las contenidas en p.
        Util para resolver las queries con NOT.


        param:  "p": posting list


        return: posting list con todos los artid exceptos los contenidos en p

        """
        news = self.news.keys()
        p = [newId for newId, f in p]
        return [[newId,0] for newId in news if newId not in p]
      
        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################



    def and_posting(self, p1:list, p2:list):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Calcula el AND de dos posting list de forma EFICIENTE

        param:  "p1", "p2": posting lists sobre las que calcular


        return: posting list con los artid incluidos en p1 y p2

        """
        if p1 == [] or p2 == []: return []
        respost = []
        iP1 = 0; iP2 = 0
        while iP1 < len(p1) and iP2 < len(p2):
            dataP1 = p1[iP1]
            dataP2 = p2[iP2]
            if dataP1[0] == dataP2[0]:
                #dataP1[1] += dataP2[1]
                respost.append(dataP1)
                iP1 += 1; iP2 += 1
            elif dataP1[0] > dataP2[0]:
                iP2 += 1
            else:
                iP1 += 1
        return respost
       
        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################



    def or_posting(self, p1:list, p2:list):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Calcula el OR de dos posting list de forma EFICIENTE

        param:  "p1", "p2": posting lists sobre las que calcular


        return: posting list con los artid incluidos de p1 o p2

        """
        respost = []
        iP1 = 0; iP2 = 0
        while iP1 < len(p1) and iP2 < len(p2):
            dataP1 = p1[iP1]
            dataP2 = p2[iP2]
            if dataP1[0] == dataP2[0]:
                respost.append(dataP1)
                iP1 += 1; iP2 += 1
            elif dataP1[0] > dataP2[0]:
                respost.append(dataP2)
                iP2 += 1
            else:
                respost.append(dataP1)
                iP1 += 1

        while iP1 < len(p1):
            respost.append(p1[iP1])
            iP1 += 1
        while iP2 < len(p2):
            respost.append(p2[iP2])
            iP2 += 1

        return respost
    
        ########################################
        ## COMPLETAR PARA TODAS LAS VERSIONES ##
        ########################################


    def minus_posting(self, p1, p2):
        """
        OPCIONAL PARA TODAS LAS VERSIONES

        Calcula el except de dos posting list de forma EFICIENTE.
        Esta funcion se incluye por si es util, no es necesario utilizarla.

        param:  "p1", "p2": posting lists sobre las que calcular


        return: posting list con los artid incluidos de p1 y no en p2

        """
        iP1 = 0; iP2 = 0
        while iP1 < len(p1) and iP2 < len(p2):
            dataP1 = p1[iP1]
            dataP2 = p2[iP2]
            if dataP1[0] == dataP2[0]:
                p1.pop(iP1)
                iP2 += 1
            elif dataP1[0] > dataP2[0]:
                iP1 += 1
            else:
                iP2 += 1
        return p1

        ########################################################
        ## COMPLETAR PARA TODAS LAS VERSIONES SI ES NECESARIO ##
        ########################################################





    #####################################
    ###                               ###
    ### PARTE 2.2: MOSTRAR RESULTADOS ###
    ###                               ###
    #####################################

    def solve_and_count(self, ql:List[str], verbose:bool=True) -> List:
        results = []
        for query in ql:
            if len(query) > 0 and query[0] != '#':
                r = self.solve_query(query)
                results.append(len(r))
                if verbose:
                    print(f'{query}\t{len(r)}')
            else:
                results.append(0)
                if verbose:
                    print(query)
        return results


    def solve_and_test(self, ql:List[str]) -> bool:
        errors = False
        for line in ql:
            if len(line) > 0 and line[0] != '#':
                query, ref = line.split('\t')
                reference = int(ref)
                result = len(self.solve_query(query))
                if reference == result:
                    print(f'{query}\t{result}')
                else:
                    print(f'>>>>{query}\t{reference} != {result}<<<<')
                    errors = True                    
            else:
                print(query)
        return not errors


    def solve_and_show(self, query:str):
        """
        NECESARIO PARA TODAS LAS VERSIONES

        Resuelve una consulta y la muestra junto al numero de resultados 

        param:  "query": query que se debe resolver.

        return: el numero de artículo recuperadas, para la opcion -T

        """

        resultado = self.solve_query(query)
        valores_distintos_docid = set(resultado['docid'])
        cantidad_valores_distintos_docid = len(valores_distintos_docid)
        print(query, "  ", cantidad_valores_distintos_docid)
        #print("Ha salido:", len(resultado), "veces")

        
        ################
        ## COMPLETAR  ##
        ################







        

