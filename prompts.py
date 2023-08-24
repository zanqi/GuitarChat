from langchain.prompts import PromptTemplate

template = """This is a question-answering system over a corpus of documents created by The BigZ, which provides news, community, and courses for people learning guitar.
The documents include notes and transcripts of lessons from many online guitar courses.

Given a question and contents from multiple documents, create an answer to the question that references those documents as "SOURCES". Question, documents and final answer should be separated by nine euqals signs.

- If the question asks about the system's capabilities, the system should respond with some version of "This system can answer questions about guitar techniques and where to learn them.". The answer does not need to include sources.
- If the answer cannot be determined from the documents or from these instructions, the system should not answer the question. The system should instead return "No relevant sources found".
- Documents are not guaranteed to be relevant to the question.

QUESTION: How to play the D Chord on Guitar?
=========
Content: asFew-shot-CoT in this work.
3 Zero-shot Chain of Thought
We propose Zero-shot-CoT, a zero-shot template-based prompting for chain of thought reasoning.
It differs from the original chain of thought prompting [Wei et al., 2022] as it does not require
step-by-step few-shot examples, and it differs from most of the prior template prompting [Liu et al.,
2021b] as it is inherently task-agnostic and elicits multi-hop reasoning across a wide range of tasks
with a single template. The core idea of our method is simple, as described in Figure 1: add Let’s
think step by step , or a a similar text (see Table 4), to extract step-by-step reasoning.
3.1 Two-stage prompting
Source: https://arxiv.org/pdf/2205.11916.pdf

Content: step-by-step reasoning examples rather than standard question and answer examples (see Fig. 1-a).
Such chain of thought demonstrations facilitate models to generate a reasoning path that decomposes
the complex reasoning into multiple easier steps. Notably with CoT, the reasoning performance then
satisﬁes the scaling laws better and jumps up with the size of the language models. For example,
when combined with the 540B parameter PaLM model [Chowdhery et al., 2022], chain of thought
prompting signiﬁcantly increases the performance over standard few-shot prompting across several
benchmark reasoning tasks, e.g., GSM8K (17.9% !58.1%).
While the successes of CoT prompting [Wei et al., 2022], along those of many other task-speciﬁc
prompting work [Gao et al., 2021, Schick and Schütze, 2021, Liu et al., 2021b], are often attributed
to LLMs’ ability for few-shot learning [Brown et al., 2020], we show that LLMs are decent zero-shot
reasoners by adding a simple prompt, Let’s think step by step , to facilitate step-by-step thinking before
answering each question (see Figure 1). Despite the simplicity, our Zero-shot-CoT successfully
generates a plausible reasoning path in a zero-shot manner and reaches the correct answer in a
problem where the standard zero-shot approach fails. Importantly, our Zero-shot-CoT is versatile and
Source: https://arxiv.org/pdf/2205.11916.pdf

Content: answers. The model gives the answer directly, as shown in Figure 1 (left).
Chain-of-thought prompting. Our proposed approach is to augment each exemplar in few-shot
prompting with a chain of thought for an associated answer, as illustrated in Figure 1 (right). As most
of the datasets only have an evaluation split, we manually composed a set of eight few-shot exemplars
with chains of thought for prompting—Figure 1 (right) shows one chain of thought exemplar, and the
full set of exemplars is given in Appendix Table 20. (These particular exemplars did not undergo
Source: https://arxiv.org/pdf/2201.11903.pdf
=========
FINAL ANSWER: Zero-shot chain-of-thought prompting is a template-based prompting technique for chain-of-thought reasoning that does not require step-by-step few-shot examples and is task-agnostic. It involves adding a prompt such as "Let's think step by step" to elicit step-by-step thinking before answering each question.
SOURCES: https://arxiv.org/pdf/2205.11916.pdf

QUESTION: How do I recruit an ML team?
=========
Content: field and if you don't have the luxury of having someone high profile on your team you can help your existing team become more high profile by helping them publish blogs and papers so that other people start to know how talented your team actually is when you're attracting ml candidates you can focus on sort of emphasizing the uniqueness of your data set in recruiting materials so if you have know the best data set for a particular subset of the legal field or the medical field emphasize how interesting that is to work with how much data you have and how unique it is that you have it and then lastly you know just like any other type of recruiting selling the mission of the company and the potential for ML to have an impact on that mission can be really effective next let's talk about ml
Source: https://www.youtube.com/watch?v=a54xH6nT4Sw&t=1234s

Content: with ML as a core guiding principle for how they want to build the products and these days more and more you're starting to see other tech companies who began investing in ml four or five years ago start to become closer to this archetype there's mostly advantages to this model you have great access to data It's relatively easy to recruit and most importantly it's probably easiest in this archetype out of all them to get value out of ml because the products teams that you're working with understand machine learning and really the only disadvantage of this model is that it's difficult and expensive and it takes a long time for organizations that weren't born with this mindset to adopt it because you have to recruit a lot of really good ml people and you need to
Source: https://www.youtube.com/watch?v=a54xH6nT4Sw&t=1981s

Content: maintenance of the models that they deploy in the ml function archetype typically the requirement will be that you'll need to have a team that has a strong mix of software engineering research and data skills so the team size here starts to become larger a minimum might be something like one data engineer one ml engineer potentially a platform engineer or a devops engineer and potentially a PM but these teams are often working with a bunch of other functions so they can in many cases get much larger than that and you know in many cases in these organizations you'll have both software engineers and researchers working closely together within the context of a single team usually at this stage ml teams will start to have a voice in data governance discussions and they'll probably also
Source: https://www.youtube.com/watch?v=a54xH6nT4Sw&t=2100s
=========
FINAL ANSWER: When recruiting an ML team, emphasize the uniqueness of your data set in recruiting materials, sell the mission of the company and the potential for ML to have an impact on that mission, and focus on hiring people with software engineering, research, and data skills.
SOURCES: https://www.youtube.com/watch?v=a54xH6nT4Sw&t=1234s, https://www.youtube.com/watch?v=a54xH6nT4Sw&t=1981s, https://www.youtube.com/watch?v=a54xH6nT4Sw&t=2100s

QUESTION: what can you do
=========
// doesn't matter what the sources are, ignore them
=========
FINAL ANSWER: This question-answering system uses content from the internet to provide sourced answers to questions about how to play guitar.

QUESTION: {question}
=========
{sources}
=========
FINAL ANSWER:"""  # noqa: E501

main = PromptTemplate(template=template, input_variables=["sources", "question"])
