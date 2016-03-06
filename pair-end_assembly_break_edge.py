import re,sys,pdb
import networkx as nx
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pygraphviz

# 2015.12.08
# Use MultiDiGraph to add the paired-end information
# Use the new collapse method: collapse if two reads belong to the same genome
# 2015.12.07
# Use the mapped results of each read
# Calculate the node coverage and pair-end information
# the function for plotting the reads overlap generated by readjoiner
# 1. prefilter -des to produce the reads mapping between original IDs and new IDs
# 2. spmtest to extract the overlap smp file
# Collapsing nodes to outstand bifurcations in the graph

# 2016.02.25
# depth first search for assembly
# 2016.03.06
# break some edges based on pair-end infor

color_dict={'89.6':'#DC143C','HXB2':'#FF83FA','JRCSF':'#ED9121','NL43':'#EEEE00','YU2':'#00FF7F'}

def get_seq_from_fa(fa_file,des_file):
    read_map={}  # key: read_name, value: read_index
    read_name_list=[] # read names
    count=0
    with open(des_file,'r') as f:
        for line in f:
            # HCV_1-163200/1
            read_map[line[:-1]]=str(count)
            read_name_list.append(line[:-1])
            count+=1

    seq_dict={}  # key: read_index, value: the corresponding sequence
    with open(fa_file,'r') as f:
        for line in f:
            if line.startswith('>'):
                read_id=line[1:].split()[0]
                if read_id in read_map:
                    read_num=read_map[read_id]
                    seq_dict[read_num]=""
            else:
                if read_id in read_map:
                    read_num=read_map[read_id]
                    seq_dict[read_num]+=line[:-1]
    return read_name_list,read_map,seq_dict

def create_graph_with_fq(edge_file,des_list,read_node_dict):
    # create the initial graph, node name: read_index
    # read_node_dict: store the corresponding node for each read
    # des_list: the list storing the read_name

    G = nx.MultiDiGraph()

    with open(edge_file,'r') as f:
        for line in f:
            if "-" in line:
                continue
            
            read_1, read_2, overlap_len=line.strip().split(' + ')
            #read_id_1, read_id_2=read_map[read_1],read_map[read_2]
            #if int(read_1)<5000 and int(read_2)<5000:
            if read_1 not in G.nodes():
                virus_name=des_list[int(read_1)].split('-')[0:-1]
                if len(virus_name)==1 and virus_name[0] in color_dict:
                    color_node=color_dict[virus_name[0]]
                else:
                    color_node='black'
                    #pdb.set_trace()

                read_id=des_list[int(read_1)].split('-')[-1:]

                read_name=read_id[0]
                if read_name.endswith('1'):
                    if not read_name.split('/')[0] in read_node_dict:
                        read_node_dict[read_name.split('/')[0]]=[read_1,'']
                    else:
                        read_node_dict[read_name.split('/')[0]][0]=read_1

                else:
                    if not read_name.split('/')[0] in read_node_dict:
                        read_node_dict[read_name.split('/')[0]]=['',read_1]
                    else:
                        read_node_dict[read_name.split('/')[0]][1]=read_1


                G.add_node(read_1,species=virus_name,read_ids=read_id,color=color_node,penwidth='1.5')
                #G.node[read_id_1]['shape']='box'
            if read_2 not in G.nodes():
                virus_name=des_list[int(read_2)].split('-')[0:-1]
                if len(virus_name)==1 and virus_name[0] in color_dict:
                    color_node=color_dict[virus_name[0]]
                else:
                    color_node='black'
                    #pdb.set_trace()

                read_id=des_list[int(read_2)].split('-')[-1:]

                read_name=read_id[0]
                if read_name.endswith('1'):
                    if not read_name.split('/')[0] in read_node_dict:
                        read_node_dict[read_name.split('/')[0]]=[read_2,'']
                    else:
                        read_node_dict[read_name.split('/')[0]][0]=read_2

                else:
                    if not read_name.split('/')[0] in read_node_dict:
                        read_node_dict[read_name.split('/')[0]]=['',read_2]
                    else:
                        read_node_dict[read_name.split('/')[0]][1]=read_2

                G.add_node(read_2,species=virus_name,read_ids=read_id,color=color_node,penwidth='1.5')
                #G.node[read_id_2]['shape']='box'
            #if int(overlap_len)>=190:
            G.add_edge(read_1,read_2,label=overlap_len,color='blue',penwidth='1')

    return G 

# species could be a string (one species for the node) or a list (more than one species for the node)
def join_species(species1,species2):
    combined_species=species1
    for name in species2:
        if not name in combined_species:
            combined_species.append(name)
    return combined_species

def compare_list(list1,list2):
    return sorted(list1)==sorted(list2)

def collapse_graph(G, candidates,read_db, read_node_dict):
    # node collapsed: combined node
    # read_node_dict: store the corresponding node for each read, key: read_base, value: [.1 node, .2 node]
    while True:
        nodes_to_combine = []
        if not candidates:
            all_node = G.nodes()
        else:
            all_node = candidates

        for node in all_node:
            #pdb.set_trace()
            if G.in_degree(node) == 1 and G.out_degree(G.predecessors(node)[0]) == 1:
                predecessor = G.predecessors(node)[0]
                if compare_list(G.node[node]['species'],G.node[predecessor]['species']):
                    nodes_to_combine.append(node)
                    if candidates:
                        candidates.remove(node)

        if not nodes_to_combine:
            break

        for node_to_combine in nodes_to_combine:
            if G.in_degree(node_to_combine)==0:
                pdb.set_trace()

            predecessor = G.predecessors(node_to_combine)[0]
            predecessors_predecessors = G.predecessors(predecessor)
            successors = G.successors(node_to_combine)

            # update graph
            ## update species
            pre_species=G.node[predecessor]['species']
            node_to_combine_species=G.node[node_to_combine]['species']
            
            if compare_list(pre_species,node_to_combine_species):
                combined_species=join_species(pre_species,node_to_combine_species)
            else:
                continue

            ## update read id
            combined_read_ids=G.node[predecessor]['read_ids']
            #if pre_read_ids==None:
            #    pdb.set_trace()
            combined_read_ids.extend(G.node[node_to_combine]['read_ids'])

            ## update node
            if node_to_combine.find('|')>-1 and predecessor.find('|')==-1:
                combined_node = predecessor+'|'+str(int(node_to_combine.split('|')[1])+1)

            elif node_to_combine.find('|')>-1 and predecessor.find('|')>-1:
                combined_node = predecessor.split('|')[0]+'|'+str(int(predecessor.split('|')[1])+int(node_to_combine.split('|')[1])+1)
            elif predecessor.find('|')>-1 and node_to_combine.find('|')==-1:
                combined_node = predecessor.split('|')[0]+'|'+str(int(predecessor.split('|')[1])+1)
            else:
                combined_node = predecessor +'|'+str(1)
            #pdb.set_trace()
           
            ## update read_node_dict
            for read in combined_read_ids:
                if read.endswith('1'):
                    read_node_dict[read.split('/')[0]][0]=combined_node
                else:
                    read_node_dict[read.split('/')[0]][1]=combined_node

            if len(combined_species)==1:
                color_node=color_dict[combined_species[0]]
            else:
                color_node='black'
            G.add_node(combined_node,species=combined_species,read_ids=combined_read_ids,color=color_node,penwidth='2.0')
            for predecessors_predecessor in predecessors_predecessors:
                o = G[predecessors_predecessor][predecessor][0]["label"]
                G.add_edge(predecessors_predecessor, combined_node, label= o, color='blue', penwidth='2.0')

            for successor in successors:
                o = G[node_to_combine][successor][0]["label"]
                G.add_edge(combined_node, successor, label= o, color='blue', penwidth='2.0')

            # update sequences
            overlap_to_predecessor = int(G[predecessor][node_to_combine][0]["label"])
            offset = len(read_db[predecessor]) - overlap_to_predecessor

            pred_seq = read_db[predecessor]
            node_seq = read_db[node_to_combine]
            combined_seq = pred_seq + node_seq[overlap_to_predecessor:]

            read_db[combined_node] = combined_seq

            # clean up
            G.remove_node(node_to_combine)
            G.remove_node(predecessor)

            del read_db[node_to_combine]
            del read_db[predecessor]

            if node_to_combine in nodes_to_combine:
                nodes_to_combine.remove(node_to_combine)
            if predecessor in nodes_to_combine:
                nodes_to_combine.remove(predecessor)
    return G

def get_assemblie(G,read_db):
    contigs={}
    if len(G.nodes())>1:
        starting_nodes=[n for n in G.nodes() if G.in_degree(n)==0]
        ending_nodes=[n for n in G.nodes() if G.out_degree(n)==0]

        paths=[]
        for start_node in starting_nodes:
            for end_node in ending_nodes:
                two_nodes_paths=nx.all_simple_paths(G,start_node,end_node)

                for path in two_nodes_paths:
                    print path
                    contig_key='contig_'+':'.join(path)
                    contigs[contig_key]=read_db[path[0]]
                    for idx in range(1,len(path)):
                        prev,current=path[idx-1],path[idx]
                        seq=read_db[current]
                        #pdb.set_trace()
                        overlap=int(G[prev][current]["label"])
                        contigs[contig_key]+=seq[overlap:]
                    #contigs.append(contig)
    else:
        contig_key='contig_'+G.nodes()[0]
        contigs[contig_key]=read_db[G.nodes()[0]]

    return contigs

def is_false_connection(G,node1,node2,paired_end_dict):
    # decide whether (node1,node2) is a false connection in G based on paired-end information
    flag = 1  # 1: is false connection, no paired-end evidence; 0: is not false connection
    predecessors=G.predecessors(node1)
    if (node1,node2) in paired_end_dict or (node2,node1) in paired_end_dict:
        flag=0
    for pre_node in predecessors:
        if (pre_node,node2) in paired_end_dict or (node2, pre_node) in paired_end_dict:
            flag=0
    predecessor_set=[]
    successor_set=[]
    predecessors=G.predecessors(node1)
    return flag

'''def DFS_iterative(G, start_node, path_dict={},path=[]):
    q=[start_node]
    while q:
        v=q.pop(0)
        if v not in path:
            path=path+[v]
            path_dict[(start_node,v)]=path

            successors=G.successors(v)
            if len(successors)>1:'''

def DFS_paths_interative(G, start_node, end_node):
    stack=[(start_node,[start_node])]
    while stack:
        (vertex, path)=stack.pop()
        for succ_node in set(G.successors(vertex)) - set(path):
            #pdb.set_trace()
            if succ_node==end_node:
                yield path+[succ_node]
            else:
                stack.append((succ_node,path+[succ_node]))

def get_paired_score(path,succ_node,paired_end_edges):
    paired_score1,paired_score2=0,0
    for this_node in path[0:-1]:
        if (this_node,succ_node) in paired_end_edges: 
            paired_score1+=paired_end_edges[(this_node,succ_node)]
        elif (succ_node,this_node) in paired_end_edges:
            paired_score1+=paired_end_edges[(succ_node,this_node)]
    if (path[-1],succ_node) in paired_end_edges:
        paired_score2+=paired_end_edges[(path[-1],succ_node)]
    elif (succ_node,path[-1]) in paired_end_edges:
        paired_score2+=paired_end_edges[(succ_node,path[-1])]

    return paired_score1,paired_score2

def get_paired_connection_score(path,succ_node,PE_node_dict):
    score1,score2=0,0
    if not succ_node in PE_node_dict:
        return 0,0
    else:
        for this_node in path[0:-1]:
            if this_node in PE_node_dict and PE_node_dict[this_node]==PE_node_dict[succ_node]:
                score1+=1
        if path[-1] in PE_node_dict and PE_node_dict[path[-1]]==PE_node_dict[succ_node]:
            score2+=1
        return score1,score2

def create_paired_end_connection(subgraph_paired_end_edges):
    PE_node_dict={}
    PE_group=[]
    PE_G=nx.Graph()
    idx=0
    for pair in subgraph_paired_end_edges:
        PE_G.add_edge(pair[0],pair[1])
    PE_subgraphs_nodes=nx.connected_components(PE_G)
    for PE_graph_nodes in PE_subgraphs_nodes:
        PE_group.append(PE_graph_nodes)
        for node in PE_graph_nodes:
            if not node in PE_node_dict:
                PE_node_dict[node]=idx
        idx+=1
    return PE_node_dict,PE_group

# using paired-end information for paths searching
# rule 1: if the new node has connection to the path except its direct predecessor (denote as pre-path), add the new node to the path
# rule 2: if the new node has no connection to the pre-path but the direct predecessor, do not add the new node to the path
def DFS_paths_paired_end(G, start_node, end_node,paired_end_edges,PE_node_dict,candidate_delete_edge):
    # PE_node_dict: the index of group for each node, key: node, value: index, group: pair-end connected groups
    stack=[(start_node,[start_node])]
    #candidate_delete_edge={}:  if one node has no pair-end connections to the path, consider to delete the overlap edge
    while stack:
        (vertex, path)=stack.pop()
        succ_node_all = set(G.successors(vertex)) - set(path)
        if len(succ_node_all)>1: # seeing a bifurcation node, multiple successors, judge which one to append
            flag=0
            for succ_node in succ_node_all:
                #if start_node=='[HXB2][28.11][370]8318|51' and succ_node=='[HXB2][85.96][1268]6164|544' and vertex=='[HXB2,NL43][27.78][288]8864|39':
                #    pdb.set_trace()
                score1,score2=get_paired_score(path,succ_node,paired_end_edges)
                connect_score1,connect_score2=get_paired_connection_score(path,succ_node,PE_node_dict)
                if succ_node==end_node: # reaching the end
                    if score1>0:
                        yield path+[succ_node]
                    elif connect_score1>0:
                        yield path+[succ_node]
                    elif score2>0:
                        print "1"
                        #yield path[-1:]+[succ_node]
                        #print "1. Path:",path
                        #print "succ_node:",succ_node
                    elif connect_score2>0:
                        print "1"
                        #print "2. Path:",path
                        #print "succ_node:",succ_node
                    else:
                        flag+=1
                        print "No connection succint node (1):",path,succ_node
                        #G.remove_edge(path[-1],succ_node)  
                        if (path[-1],succ_node) not in candidate_delete_edge:
                            candidate_delete_edge[(path[-1],succ_node)]=succ_node
                else:                    # not reaching the end
                    if score1>0:
                        stack.append((succ_node,path+[succ_node]))
                    elif connect_score1>0:
                        stack.append((succ_node,path+[succ_node]))
                    elif score2>0:
                        print "1"
                        #pdb.set_trace()
                        #stack.append((succ_node,path[-1:]+[succ_node]))
                        #print "1_middle. Path:",path
                        #print "succ_node:",succ_node
                    elif connect_score2>0:
                        print "1"
                        #print "2_middle. Path:",path
                        #print "succ_node:",succ_node
                    else:
                        flag+=1
                        print "No connection succint node (2_middle):",path,succ_node
                        #G.remove_edge(path[-1],succ_node)  # no connection to either pre-path or predecessor, remove the edge
                        #G.add_edge(path[-1],succ_node,color='red',penwidth='2')
                        if (path[-1],succ_node) not in candidate_delete_edge:
                            candidate_delete_edge[(path[-1],succ_node)]=succ_node
                if flag==len(succ_node_all): # cannot extend to any of the next node
                    #yield path
                    print "Break middle node found!",vertex
                    #pdb.set_trace()

        elif len(succ_node_all)==1: # just one successor, append to the path
            for succ_node in succ_node_all:
                if succ_node==end_node:
                    yield path+[succ_node]
                else:
                    stack.append((succ_node,path+[succ_node]))
        else:                       # finding a cycle
            print "Finding a cycle!",path
            yield path

# with just the start_node, find all the paths
def DFS_paths_paired_end2(G, start_node, paired_end_edges,PE_node_dict,candidate_delete_edge):
    # PE_node_dict: the index of group for each node, key: node, value: index, group: pair-end connected groups
    stack=[(start_node,[start_node])]
    #candidate_delete_edge={}:  if one node has no pair-end connections to the path, consider to delete the overlap edge
    while stack:
        (vertex, path)=stack.pop()
        succ_node_all = set(G.successors(vertex)) - set(path)
        if len(succ_node_all)>1: # seeing a bifurcation node, multiple successors, judge which one to append
            flag=0
            for succ_node in succ_node_all:
                if start_node=='[HXB2][28.11][370]8318|51' and succ_node=='[HXB2][85.96][1268]6164|544' and vertex=='[HXB2,NL43][27.78][288]8864|39':
                    pdb.set_trace()
                score1,score2=get_paired_score(path,succ_node,paired_end_edges)
                connect_score1,connect_score2=get_paired_connection_score(path,succ_node,PE_node_dict)
                if G.out_degree(succ_node)==0: # reaching the end
                    if score1>0:
                        yield path+[succ_node]
                    elif connect_score1>0:
                        yield path+[succ_node]
                    elif score2>0:
                        print "1"
                        #yield path[-1:]+[succ_node]
                        #print "1. Path:",path
                        #print "succ_node:",succ_node
                    elif connect_score2>0:
                        print "1"
                        #print "2. Path:",path
                        #print "succ_node:",succ_node
                    else:
                        flag+=1
                        print "No connection succint node (1):",path,succ_node
                        #G.remove_edge(path[-1],succ_node)  
                        if (path[-1],succ_node) not in candidate_delete_edge:
                            candidate_delete_edge[(path[-1],succ_node)]=succ_node
                else:                    # not reaching the end
                    if score1>0:
                        stack.append((succ_node,path+[succ_node]))
                    elif connect_score1>0:
                        stack.append((succ_node,path+[succ_node]))
                    elif score2>0:
                        print "1"
                        #pdb.set_trace()
                        #stack.append((succ_node,path[-1:]+[succ_node]))
                        #print "1_middle. Path:",path
                        #print "succ_node:",succ_node
                    elif connect_score2>0:
                        print "1"
                        #print "2_middle. Path:",path
                        #print "succ_node:",succ_node
                    else:
                        flag+=1
                        print "No connection succint node (2_middle):",path,succ_node
                        #G.remove_edge(path[-1],succ_node)  # no connection to either pre-path or predecessor, remove the edge
                        #G.add_edge(path[-1],succ_node,color='red',penwidth='2')
                        if (path[-1],succ_node) not in candidate_delete_edge:
                            candidate_delete_edge[(path[-1],succ_node)]=succ_node
                if flag==len(succ_node_all): # cannot extend to any of the next node
                    #yield path
                    print "Break middle node found!",vertex
                    #pdb.set_trace()

        elif len(succ_node_all)==1: # just one successor, append to the path
            for succ_node in succ_node_all:
                if G.out_degree(succ_node)==0:
                    yield path+[succ_node]
                else:
                    stack.append((succ_node,path+[succ_node]))
        else:                       # finding a cycle, break and report the path
            print "Finding a cycle:", path
            yield path 


def get_assemblie2(G,read_db):
    contigs={}
    if len(G.nodes())>1:
        starting_nodes=[n for n in G.nodes() if G.in_degree(n)==0]
        ending_nodes=[n for n in G.nodes() if G.out_degree(n)==0]

        paths=[]
        for start_node in starting_nodes:
            for end_node in ending_nodes:
                two_nodes_paths=[]
                for path in DFS_paths_interative:
                    two_nodes_paths.append(path)

                for path in two_nodes_paths:
                    print path
                    contig_key='contig_'+':'.join(path)
                    contigs[contig_key]=read_db[path[0]]
                    for idx in range(1,len(path)):
                        prev,current=path[idx-1],path[idx]
                        seq=read_db[current]
                        #pdb.set_trace()
                        overlap=int(G[prev][current]["label"])
                        contigs[contig_key]+=seq[overlap:]
                    #contigs.append(contig)
    else:
        contig_key='contig_'+G.nodes()[0]
        contigs[contig_key]=read_db[G.nodes()[0]]

    return contigs

###########################################################################
des_file=sys.argv[1]
edge_file=sys.argv[2]
fa_file=sys.argv[3]
des_list,read_map,read_db=get_seq_from_fa(fa_file,des_file) # read dictionary

read_node_dict={}
G=create_graph_with_fq(edge_file,des_list,read_node_dict)
#pdb.set_trace()
subgraphs=nx.weakly_connected_components(G)
print "Graph construction finished!"

idx=0
#f_out=open('HCV_genome_assembl_test.txt','w')
#f_out=open('HIV_paired_end_connections.txt','w')
f_out=open('HIV_paths.txt','w')
contig_index=0
for gg in subgraphs:
    print "The nodes of original graph:",len(gg)
    subgraph_simple=collapse_graph(G.subgraph(gg),[],read_db,read_node_dict)
    print "The nodes of collapsed graph:",len(subgraph_simple)

    ## delete low overlap edges
    for this_edge in subgraph_simple.edges():
        if int(subgraph_simple.edge[this_edge[0]][this_edge[1]][0]['label'])<190:
            subgraph_simple.remove_edge(this_edge[0],this_edge[1])
    subgraph_simple=collapse_graph(subgraph_simple,[],read_db,read_node_dict)

    ## add pair-end information to the graph
    paired_end_edges={}
    for read_base in read_node_dict:
        node_1=read_node_dict[read_base][0]
        node_2=read_node_dict[read_base][1]
        if not (node_1,node_2) in paired_end_edges:
            paired_end_edges[(node_1,node_2)]=1
        else:
            paired_end_edges[(node_1,node_2)]+=1

    '''for pair in paired_end_edges:
        if pair[0] in subgraph_simple.nodes() and pair[1] in subgraph_simple.nodes():
            subgraph_simple.add_edge(pair[0],pair[1],style='dashed',label=str(paired_end_edges[pair]))'''

    ## delete edges with no pair-end supporting
    '''for this_edge in subgraph_simple.edges():
        if not (this_edge[0],this_edge[1]) in paired_end_edges and not (this_edge[1],this_edge[0]) in paired_end_edges:
            #subgraph_simple[this_edge[0]][this_edge[1]]['style']='dashed'
            #subgraph_simple[this_edge[0]][this_edge[1]]['color']='red'
            subgraph_simple.remove_edge(this_edge[0],this_edge[1])
            subgraph_simple.add_edge(this_edge[0],this_edge[1],style='dashed',color='red')'''

    ## label the nodes with species name and coverage
    node_mapping={} # key: old node, value: new node
    for this_node in subgraph_simple.nodes():
        species_name=subgraph_simple.node[this_node]['species']
        if len(species_name)>1:
            print '>'+this_node
            print subgraph_simple.node[this_node]['read_ids']
        species_name=",".join(species_name)

        node_read_num=len(subgraph_simple.node[this_node]['read_ids'])
        node_coverage=200.0*node_read_num/float(len(read_db[this_node]))
        node_coverage=round(node_coverage,2)
        new_node='['+species_name+']'+'['+str(node_coverage)+']'+'['+str(len(read_db[this_node]))+']'+this_node
        if not this_node in node_mapping:
            node_mapping[this_node]=new_node
        else:
            print "Node mapping error!"
    subgraph_simple=nx.relabel_nodes(subgraph_simple,node_mapping)
    #nx.write_dot(subgraph,'multi.dot')

    # replace the nodes information in paired_end_edges
    subgraph_paired_end_edges={}
    for key in paired_end_edges:
        if key[0] in node_mapping and key[1] in node_mapping:
            subgraph_paired_end_edges[(node_mapping[key[0]],node_mapping[key[1]])]=paired_end_edges[key]
    print "subgraph_paired_end_edges",len(subgraph_paired_end_edges)

    ## 
    PE_node_dict,PE_group=create_paired_end_connection(subgraph_paired_end_edges)
    # ---- test group output ----
    f_out_group=open('pair-end_groups.txt','w')
    for group in PE_group:
        out_line="--".join(group)
        f_out_group.write(out_line+'\n')
    f_out_group.close()
    # ---- end of test----

    starting_nodes=[n for n in subgraph_simple.nodes() if subgraph_simple.in_degree(n)==0]
    ending_nodes=[n for n in subgraph_simple.nodes() if subgraph_simple.out_degree(n)==0]
    assembled_nodes=set([])
    candidate_delete_edges={}
    for start_node in starting_nodes:
        for end_node in ending_nodes:
            print "Begin a new group of start and end nodes:",start_node,end_node
            paths=list(DFS_paths_paired_end(subgraph_simple,start_node,end_node,subgraph_paired_end_edges,PE_node_dict,candidate_delete_edges))
            #pdb.set_trace()
            for path in paths:
                assembled_nodes=assembled_nodes.union(set(path))
                out_path="--".join(path)
                f_out.write(out_path+'\n')
                #print path

    ## remove unsupported edges
    for edge in candidate_delete_edges:
        if edge[1] not in assembled_nodes:
            subgraph_simple.remove_edge(edge[0],edge[1])
            #subgraph_simple.add_edge(edge[0],edge[1],color='red',penwidth='2')

    ## new starting nodes
    starting_nodes2=[n for n in subgraph_simple.nodes() if subgraph_simple.in_degree(n)==0]
    ending_nodes2=[n for n in subgraph_simple.nodes() if subgraph_simple.out_degree(n)==0]
    new_starts=list(set(starting_nodes2)-set(starting_nodes))
    print "New starting nodes:",new_starts
    for start_node in new_starts:
        for end_node in ending_nodes2:
            print "Begin a new group of start and end nodes:",start_node,end_node
            paths=list(DFS_paths_paired_end(subgraph_simple,start_node,end_node,subgraph_paired_end_edges,PE_node_dict,candidate_delete_edges))
            #pdb.set_trace()
            for path in paths:
                assembled_nodes=assembled_nodes.union(set(path))
                out_path="--".join(path)
                f_out.write(out_path+'\n')
                print "New Path:",path

    if len(set(subgraph_simple.nodes())-assembled_nodes)>0:
        print "Unassembled nodes!",set(subgraph_simple.nodes())-assembled_nodes
    
    pdb.set_trace() 
    ## output the paired-end information in a text file
    '''new_paired_end_edges={}
    for pair in paired_end_edges:
        if pair[0] in node_mapping.keys() and pair[1] in node_mapping.keys():
            new_paired_end_edges[pair]=paired_end_edges[pair]
    for pair in sorted(new_paired_end_edges.keys()):
        f_out.write(node_mapping[pair[0]]+'\t'+node_mapping[pair[1]]+'\t'+str(paired_end_edges[pair])+'\n')'''

    ## plot the subgraph
    '''subgraph=nx.drawing.nx_agraph.to_agraph(subgraph_simple)
    idx+=1
    figname='HIV_collapse_label_large_overlap_paired_end_break_edge_'+str(2)+'_test.png'
    subgraph.draw(figname,prog='dot')'''

    ## assemble contigs from the subgraph
    '''contigs=get_assemblie(subgraph_simple,read_db)  # a dictionary, key: path information, value: assembled sequence
    for contig_key in contigs:
        title='>'+contig_key+'_'+str(len(contigs[contig_key]))+'_'+str(contig_index)
        f_out.write(title+'\n'+contigs[contig_key]+'\n')
        contig_index+=1'''

f_out.close()

