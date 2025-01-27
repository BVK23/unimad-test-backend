from .models import UnibotHistory
import vertexai
from vertexai.generative_models import GenerativeModel, Content, Part
import re
import logging
from google.api_core.exceptions import ResourceExhausted
import uuid

# Set up logger
logger = logging.getLogger(__name__)

vertexai.init(project="unimadtest", location="us-central1")

def generate_context(user_profile, section_name):
    
    if section_name == 'skills':    
        context= '''You are "Unibot," the personal career strategist for users of Unimad / unimad.ai, an AI platform focused on helping users land their dream role. 
        In this instance you specialise in skills analysis for any user. 
        Your only objective in this instance is to give top 20 trending technical skills/languages/toolnames in the market based on users education and desired job role to include in their skill section of resume.
        Each suggestion should contain either a tool name or skill, not both.
        Never use brackets in your skills in json object.
        When user greet and initiate conversation, acknowledge in a friendly tone and guide them like a mentor. 
        You are a contextually strong bot and will never answer to unrelated queries. If a query is unrelated to skills, politely guide the user to the main Unibot (/uniboard/home). Importantly, at the end of every response, you **must** mandatorily provide the suggested skills in that response as a JSON array in the following format:
        ```json
        {
            "data": [ "skill1", "skill2", "skill3", "skill4", ... ]
        }         
        ```
        This Json object is for internal website purposes. Do not include any mention that this is a JSON object or any metadata about it'''
        gen_conf= {
        "max_output_tokens": 2048,
        "temperature": 1,
        "top_p": 1,
        }        

    elif section_name == 'education':
        context= '''You are "Unibot," the personal career strategist for users of Unimad / unimad.ai, an AI platform focused on helping users land their dream role. In this instance you specialise in optimising users educational background presentations. Your only Focus should be on making my education section polished and professional. 
        Example format: Degree: [Degree Title], Institution: [University/College], Location: [City, State/Country], Dates: [Start Date] - [End Date], Coursework: Include modules relevant to my desired role, Section: Highlight my achievements and relevance. When I greet and initiate conversation, acknowledge in a friendly tone , evaluate and seek additional details of my education if needed by asking super relevant questions and guide me like a mentor. You are a contextually strong bot and will never answer to unrelated queries. If a query is unrelated to education, politely guide me to the main Unibot (/uniboard/home).''' 
        gen_conf= {
        "max_output_tokens": 2048,
        "temperature": 1,
        "top_p": 1,
        }

    elif section_name.startswith("home"):
        context= '''You are Unibot, a personal career strategist for users of Unimad.ai. 
        Your mission is to assist users in streamlining their job preparation process by offering personalized, AI-powered support. 
        You guide users through building professional resumes, optimising LinkedIn profiles, creating portfolios, and generating tailored applications such as cover letters and cold emails. 
        Designed to provide real-time, contextual assistance, you engage users through interactive conversations that adapt to their individual goals and inputs and will ensure every interaction is focused, helpful, and easy to follow.
        Your primary goal is to reduce the complexity of career preparation and empower users to present their best selves confidently to recruiters and employers. 
        With a friendly, approachable style, you offer actionable insights and recommendations, helping users enhance their professional profiles, networking efforts, and job applications.
        You are a strong bot and will not answer unrelated queries. If any query is unrelated to your specialization politely refuse to response the user" '''
        gen_conf= {
        "max_output_tokens": 2048,
        "temperature": 1,
        "top_p": 1,
        }

    else:
        context= '''You are "Unibot," a specialized AI designed to assist users in optimizing their resumes, LinkedIn profiles, portfolios, cover letters, and LinkedIn posts. 
        Your role involves analyzing user-provided information, such as education, desired roles, past experiences, and skills. 
        You refine resume sections for clarity and impact, suggest relevant job roles and skills, and explain their suitability. 
        Additionally, you guide users in optimizing their LinkedIn profiles, generating professional portfolios, crafting impactful cover letters, and creating engaging LinkedIn posts. 
        You should not answer the irrelevant queries and ask user to provide relevant queries.'''
        gen_conf= {
        "max_output_tokens": 2048,
        "temperature": 1,
        "top_p": 1,
        }
        
    return context,gen_conf

def generate_input_prompt(user_profile, section_name, user_input, data=None):
    # Set data to an empty dictionary if not provided
    if data is None:
        data = {}

    if section_name not in ["connect", "comment", "coverpicture", "headline"] and user_input != "":
        return user_input    
    
    skills_submission = ["Python", "JavaScript", "React", "Node.js", "SQL", "Git", "Docker", "Kubernetes", "AWS", "CI/CD", "DevOps", "Cloud Computing", "Data Science", "Machine Learning", "Deep Learning", "Artificial Intelligence", "Computer Vision", "Natural Language Processing", "Robotics", "Blockchain", "Web3", "NFTs", "DeFi", "Game Development", "Unity", "Unreal Engine", "Blender", "3D Modeling", "3D Printing", "Arduino", "Raspberry Pi", "IoT", "Robotics", "Automation", "Automation Anywhere", "UiPath", "Selenium", "Cybersecurity", "Ethical Hacking", "Penetration Testing", "Network Security", "Cloud Security", "Data Security", "AI Ethics", "AI Safety", "AI Governance", "AI Policy", "AI Regulation", "AI Ethics", "AI Safety", "AI Governance", "AI Policy", "AI Regulation"]  
    education_submission = [{"course": "B.Tech", "institute": "IIT Bombay", "startDate": "2018", "endDate": "2022", "location": "Mumbai", "courseWork": "Computer Science and Engineering"}]
    experience_submission = [{"role": "Software Engineer", "organisation": "Google", "location": "San Francisco", "startDate": "2022", "endDate": "2023", "descriptions": "Developed and maintained web applications using React and Node.js"}]
    projects_submission = [{"title": "Project 1", "descriptions": "Developed a web application using React and Node.js", "startDate": "2022", "endDate": "2023"}]
    role_submission = ["Software Engineer"]

    # Extract and format content from the submissions
    skills = ", ".join(skills_submission.content) if skills_submission and isinstance(skills_submission.content, list) else 'N/A'
    
    experience = ""
    if experience_submission and isinstance(experience_submission.content, list):
        experience = "; ".join([f"{exp.get('role', '')} at {exp.get('organisation', '')}, {exp.get('location', '')} ({exp.get('startDate', '')} - {exp.get('endDate', '')}): {exp.get('descriptions', '')}" for exp in experience_submission.content])
    else:
        experience = 'N/A'

    projects = ""
    if projects_submission and isinstance(projects_submission.content, list):
        projects = "; ".join([f"{proj.get('title', '')}: {proj.get('descriptions', '')}" for proj in projects_submission.content])
    else:
        projects = 'N/A'

    education = ""
    if education_submission and isinstance(education_submission.content, list):
        education = "; ".join([f"{edu.get('course', '')} from {edu.get('institute', '')} ({edu.get('startDate', '')} - {edu.get('endDate', '')}) at {edu.get('location', '')}, Coursework: {edu.get('courseWork', '')}" for edu in education_submission.content])
    else:
        education = 'N/A'

    if section_name=='skills':
        return f'''Hi Unibot, My name is {user_profile.preferred_name}. my desired role is {user_profile.role or 'N/A'}, and i did my {user_profile.course} at {user_profile.uni}. 
        I want you to suggest the relevant skills/tools based on my education and my desired role that I need to include in my skills section of resume in order to increase my chance of converting an interview and give short explanation why they are a good fit for me?
        '''
    
    elif section_name=='role':
        return f'''Hi Unibot, My name is {user_profile.preferred_name}. Here are my education details: {education}, skills: {skills}, experience: {experience}, projects: {projects}, and my desired role: {user_profile.role}. Start with "Hey {user_profile.preferred_name} !" and I want you to suggest relevant roles that I can apply for that matches my profile.
        Keep your explanation less than 300 words'''
    

    elif section_name =='home':
        return f'''Introduce yourself in a short and friendly manner to user : {user_profile.preferred_name}"'''

    else:
        return f'''Hi Unibot! My name is {user_profile.preferred_name}. Start with "Hey {user_profile.preferred_name} !" and ask me like "How can I help you with your {section_name}" within 10 words meaningfully.
'''
    
def get_message_history_and_tokens(user_profile, section_name, token_limit=26000):
    # Fetch past messages ordered by oldest to newest
    past_messages = UnibotHistory.objects.filter(user=user_profile, section_name=section_name).order_by('id')

    # Initialize variables
    message_history = []
    total_tokens = 0

    # Always include the first message
    first_message = past_messages.first()
    if first_message:
        user_part = Part.from_text(first_message.user_message)
        bot_part = Part.from_text(first_message.bot_response)
        message_history.append(Content(role="user", parts=[user_part]))
        message_history.append(Content(role="model", parts=[bot_part]))
        total_tokens = first_message.message_tokens

    # Convert the messages (excluding the first one) to a reversed list
    reversed_messages = list(reversed(past_messages[1:]))

    # Include the newest messages first, excluding the last element (first message in the original order)
    for message in reversed_messages:
        if total_tokens + message.message_tokens <= token_limit:
            user_part = Part.from_text(message.user_message)
            bot_part = Part.from_text(message.bot_response)
            message_history.insert(2, Content(role="model", parts=[bot_part]))  # Maintain order
            message_history.insert(2, Content(role="user", parts=[user_part]))  # Maintain order
            total_tokens += message.message_tokens
        else:
            break  # Stop if adding the next message exceeds the token limit

    # Retrieve the last total tokens
    last_total_tokens = past_messages.last().total_tokens if past_messages.exists() else 0

    return message_history, last_total_tokens


def get_unibot_response(model_name, user_input, context, gen_conf, message_history=[], last_total_tokens=0):
    try:
        if model_name == "flash":
            model = GenerativeModel("gemini-1.5-flash-002", system_instruction=[context])
        elif model_name == "pro":
            model = GenerativeModel("gemini-1.5-pro-002", system_instruction=[context])
        else:
            model = GenerativeModel("gemini-1.5-flash-001", system_instruction=[context])

        # Start the chat session
        chat_session = model.start_chat(history=message_history)

        # Send a message and get response
        response = chat_session.send_message(
            content=[user_input],
            generation_config=gen_conf
        )

        # Calculate tokens for the complete response
        total_tokens = response.usage_metadata.total_token_count
        response_token_count = model.count_tokens(response.text).total_tokens

        # Calculate tokens for the current message
        if last_total_tokens == 0:
            current_message_tokens = total_tokens
        else:
            # Subsequent messages
            count_response = model.count_tokens([Content(role="user", parts=[Part.from_text(user_input)]), Content(role="model", parts=[Part.from_text(response.text)])])
            current_message_tokens = count_response.total_tokens
        
        # Return the response text and token information
        return {
            "user_input": user_input,
            "response_text": response.text,
            "total_tokens": total_tokens,
            "response_token_count": response_token_count,
            "current_message_tokens": current_message_tokens
        }
    except ResourceExhausted as e:
        # Handle token/resource exhaustion case
        logger.error(f"503: {str(e)} error occurred at unibot_window_api")
        return {"error": "Unibot service limit reached. Please try again later.", "status_code" : 503}

    except Exception as e:
        # Handle other exceptions
        logger.error(f"An 500 error occurred: {str(e)} at unibot_window_api")
        return {"error": "Internal server error. Please try again later.", "status_code" : 500}