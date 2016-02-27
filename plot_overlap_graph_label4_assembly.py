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

color_dict={'89.6':'#DC143C','HXB2':'#FF83FA','JRCSF':'#ED9121','NL43':'#EEEE00','YU2':'#00FF7F'}

def get_seq_from_fa(fa_file,des_file):
    read_map={}
    read_name_list=[]
    count=0
    with open(des_file,'r') as f:
        for line in f:
            # HCV_1-163200/1
            read_map[line[:-1]]=str(count)
            read_name_list.append(line[:-1])
            count+=1

    seq_dict={}
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
    # read_node_dict: store the corresponding node for each read

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

def DFS_iterative(G, start_node, path_dict={},path=[]):
    q=[start_node]
    while q:
        v=q.pop(0)
        if v not in path:
            path=path+[v]
            path_dict[(start_node,v)]=path

            successors=G.successors(v)
            if len(successors)>1:






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
f_out=open('HIV_paired_end_connections.txt','w')
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

    #for pair in paired_end_edges:
    #    if pair[0] in subgraph_simple.nodes() and pair[1] in subgraph_simple.nodes():
    #        subgraph_simple.add_edge(pair[0],pair[1],style='dashed',label=str(paired_end_edges[pair]))

    ## delete edges with no pair-end supporting
    for this_edge in subgraph_simple.edges():
        if not (this_edge[0],this_edge[1]) in paired_end_edges and not (this_edge[1],this_edge[0]) in paired_end_edges:
            #subgraph_simple[this_edge[0]][this_edge[1]]['style']='dashed'
            #subgraph_simple[this_edge[0]][this_edge[1]]['color']='red'
            subgraph_simple.remove_edge(this_edge[0],this_edge[1])
            subgraph_simple.add_edge(this_edge[0],this_edge[1],style='dashed',color='red')

    ## label the nodes with species name and coverage
    node_mapping={}
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
   
    ## output the paired-end information in a text file
    new_paired_end_edges={}
    for pair in paired_end_edges:
        if pair[0] in node_mapping.keys() and pair[1] in node_mapping.keys():
            new_paired_end_edges[pair]=paired_end_edges[pair]
    for pair in sorted(new_paired_end_edges.keys()):
        f_out.write(node_mapping[pair[0]]+'\t'+node_mapping[pair[1]]+'\t'+str(paired_end_edges[pair])+'\n')

    ## plot the subgraph
    subgraph=nx.to_agraph(subgraph_simple)
    idx+=1
    figname='HIV_collapse_label_large_overlap_paired_end'+str(idx)+'_test.png'
    subgraph.draw(figname,prog='dot')

    ## assemble contigs from the subgraph
    '''contigs=get_assemblie(subgraph_simple,read_db)  # a dictionary, key: path information, value: assembled sequence
    for contig_key in contigs:
        title='>'+contig_key+'_'+str(len(contigs[contig_key]))+'_'+str(contig_index)
        f_out.write(title+'\n'+contigs[contig_key]+'\n')
        contig_index+=1
f_out.close()'''
f_out.close()
