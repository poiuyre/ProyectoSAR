def start_crawling(self, initial_urls: List[str], document_limit: int,
                   base_filename: str, batch_size: Optional[int], max_depth_level: int):
    # URLs válidas, ya visitadas (se hayan procesado, o no, correctamente)
    visited = set()
    # URLs en cola
    to_process = set(initial_urls)
    # Direcciones a visitar
    queue = [(0, "", url) for url in to_process]
    hq.heapify(queue)
    # Buffer de documentos capturados
    documents: List[dict] = []
    # Contador del número de documentos capturados
    total_documents_captured = 0
    # Contador del número de ficheros escritos
    files_count = 0
    if batch_size is None:
        total_files = None
    else:
        # Suponemos que vamos a poder alcanzar el límite para la nomenclatura
        # de guardado
        total_files = math.ceil(document_limit / batch_size)

    # Proceso de captura
    while queue and total_documents_captured < document_limit:
        # Seleccionar una página no procesada de la cola de prioridad
        item = hq.heappop(queue)
        if item is not None:
            _, parent, url = item

        # Descargar el contenido textual de la página y los enlaces que aparecen en ella
        entry_content, links = self.get_wikipedia_entry_content(url)

        if entry_content is not None and links is not None:
            for link in links:
                if self.is_valid_url(link) and link not in visited:
                    hq.heappush(queue, (max_depth_level, url, link))
                    visited.add(link)
        else:
            # Añadir los enlaces a la cola de páginas pendientes de procesar
            print(f"Error al obtener el contenido y los enlaces de la pagina: {url}")

        document = self.parse_wikipedia_textual_content(entry_content, url)
        if document is not None and "title" in document and "summary" in document:
            documents.append(document)
            total_documents_captured += 1
            if batch_size is not None and len(documents) >= batch_size:
                self.save_documents(documents, f"{base_filename}_{files_count}.json")
                files_count += 1
                documents = []

    # Guardar los documentos restantes si no se alcanzó el tamaño de batch
    if documents:
        self.save_documents(documents, f"{base_filename}_{files_count}.json")

    return total_documents_captured

def start_crawlingg(self, 
                    initial_urls: List[str], document_limit: int,
                    base_filename: str, batch_size: Optional[int], max_depth_level: int,
                    ):        
         

        """Comienza la captura de entradas de la Wikipedia a partir de una lista de urls válidas, 
            termina cuando no hay urls en la cola o llega al máximo de documentos a capturar.
        
        Args:
            initial_urls: Direcciones a artículos de la Wikipedia
            document_limit (int): Máximo número de documentos a capturar
            base_filename (str): Nombre base del fichero de guardado.
            batch_size (Optional[int]): Cada cuantos documentos se guardan en
                fichero. Si se asigna None, se guardará al finalizar la captura.
            max_depth_level (int): Profundidad máxima de captura.
        """

        # URLs válidas, ya visitadas (se hayan procesado, o no, correctamente)
        visited = set()
        # URLs en cola
        to_process = set(initial_urls)
        # Direcciones a visitar
        queue = [(0, "", url) for url in to_process]
        hq.heapify(queue)
        # Buffer de documentos capturados
        documents: List[dict] = []
        # Contador del número de documentos capturados
        total_documents_captured = 0
        # Contador del número de ficheros escritos
        files_count = 0

        # En caso de que no utilicemos bach_size, asignamos None a total_files
        # así el guardado no modificará el nombre del fichero base
        if batch_size is None:
            total_files = None
        else:
            # Suponemos que vamos a poder alcanzar el límite para la nomenclatura
            # de guardado
            total_files = math.ceil(document_limit / batch_size)
         # No sea none
         	
         # Proceso de captura
        while queue and total_documents_captured < document_limit:
    
            # Seleccionar una página no procesada de la cola de prioridad
            item = hq.heappop(queue)
            if item is not None:
                _, parent, url = item	

            # Descargar el contenido textual de la página y los enlaces que aparecen en ella
            entry_content, links = self.get_wikipedia_entry_content(url)

            if entry_content is not None and links is not None:
            	for link in links:
                    if self.is_valid_url(link) and link not in visited:
                        hq.heappush(queue, (max_depth_level, url, link))
                        visited.add(link)
                    
            else:
                # Añadir los enlaces a la cola de páginas pendientes de procesar  
            	print(f"Error al obtener el contenido y los enlaces de la pagina: {url}")

            document = self.parse_wikipedia_textual_content(entry_content, url)
            if document is not None and "title" in document and "summary" in document:
                documents.append(document)
            	total_documents_captured += 1
            	if batch_size is not None and len(documents) >= batch_size:
            		self.save_documents(documents, f"{base_filename}_{files_count}.json")
            		files_count += 1
            		documents = []

        # Guardar los documentos restantes si no se alcanzó el tamaño de batch
        if documents:
            self.save_documents(documents, f"{base_filename}_{files_count}.json")
            
        return total_documents_captured