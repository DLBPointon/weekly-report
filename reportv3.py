import sys
from jira import JIRA
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta, date


def dotloader():
    load_dotenv()
    jira_user = os.getenv('JIRA_USER')
    jira_pass = os.getenv('JIRA_PASS')
    slack_add = os.getenv('SLACK_HOOK')
    return jira_user, jira_pass, slack_add


def authorise(project, user, password):
    jira = "https://grit-jira.sanger.ac.uk"
    auth_jira = JIRA(jira, basic_auth=(user, password))
    item_dict = {}
    item_list = []
    ticket_grit, ticket_rc, ticket_other, stat_today, stat_submitted = 0, 0, 0, 0, 0

    projects = auth_jira.search_issues(f'project IN ("GRIT","RC") AND type {project}', maxResults=10000)
    if len(projects) >= 1:
        for i in projects:
            issue = auth_jira.issue(f'{i}', expand='changelog')
            today = datetime.today().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S").split('T')
            for history in issue.changelog.histories:
                for item in history.items:
                    if item.toString in ['Open', 'Decontamination',
                                         'geval analysis', 'HiC Building',
                                         'gEVAL QC', 'curation',
                                         'Curation QC', 'Post Processing ++',
                                         'Submitted', 'In Submission']:

                        datetime_item = datetime \
                            .strptime(history.created,
                                      '%Y-%m-%dT%H:%M:%S.%f%z').strftime("%Y-%m-%dT%H:%M:%S").split('T')

                        time_diff = datetime.strptime(today[0],
                                                      '%Y-%m-%d') - datetime.strptime(datetime_item[0],
                                                                                      '%Y-%m-%d')
                        in_days = time_diff / timedelta(days=1)
                        end = 7 * int(sys.argv[1])
                        start = 7 * (int(sys.argv[1]) - 1)

                        if end >= int(in_days) >= start:
                            item_list.append('Today')
                            item_list.append(' @ '.join(today))
                            item_list.append(item.toString)
                            item_list.append(' @ '.join(datetime_item))
                            item_dict[f'{issue}'] = item_list
                        else:
                            pass

            item_list = []

        for i, ii in item_dict.items():
            if i.startswith('GRIT'):
                ticket_grit += 1
            elif i.startswith('RC'):
                ticket_rc += 1
            else:
                ticket_other += 1

            if ii[-2] == 'Submitted':
                stat_submitted += 1
            elif ii[-2] == 'Today':
                stat_today += 1
    proj_length = len(projects)

    return proj_length, item_dict, ticket_other, ticket_rc, ticket_grit, stat_today, stat_submitted, auth_jira


def make_json(project, BASE_MESSAGE, item_dict, ticket_other, ticket_rc, ticket_grit, stat_today, stat_submitted):
    list_of_items = ''
    message_package = f'|----- For {project[3:-1]} START-----|\n' + \
                      f'\tNothing to see for this project!\n' + \
                      f'|=================================================|\n'
    empty = True
    for i, ii in item_dict.items():
        if len(item_dict.items()) >= 1:
            list_of_items += (f'  {i} | {ii[-2]} - {ii[-1]}' + '\n')

            message_package = f'|----- For {project[3:-1]} START-----|\n' + \
                f'|=================================================|\n' + \
                f'{list_of_items}\n' + \
                f'|=================================================|\n' + \
                f' \tGRIT = {ticket_grit} || RC = {ticket_rc} || OTHER = {ticket_other}\n' + \
                f' \tSubmitted = {stat_submitted} || Opened = {stat_today}\n' + \
                f'|=================================================|\n'
            empty = False
        else:
            pass

    return message_package, empty


def new_tickets(project, auth_jira, message, empty):
    if empty is True:
        message += '\n'
    elif empty is False:
        projects = auth_jira.search_issues(f'project IN ("GRIT","RC") AND status = Open AND type {project}',
                                           maxResults=10000)
        new_list = ''
        counter = 0
        for i in projects:
            new_list += str(f'{i}, ')
            counter += 1
            if counter == 8:
                counter = 0
                new_list += ' \n '
            else:
                pass

        message += f'|===========> OPEN TICKETS <=============|\n' + \
                   f' {new_list}\n'
    else:
        message += 'ERROR\n'

    return message


def fin_tickets(project, auth_jira, message, empty):
    if empty is True:
        message += '\n'
    elif empty is False:
        projects = auth_jira.search_issues(f'project IN ("GRIT","RC") AND status = Submitted AND type {project}',
                                           maxResults=10000)
        new_list = ''
        counter = 0
        for i in projects:
            new_list += str(f'{i}, ')
            counter += 1
            if counter == 8:
                counter = 0
                new_list += ' \n '
            else:
                pass

        message += f'|===========> FIN TICKETS <=============|\n' + \
                   f' {new_list}\n' + \
                   f'|=================================================|\n'
    else:
        message = 'ERROR\n'

    return message


def post_it(json, hook):
    os.popen(f"curl -X POST -H 'Content-type: application/json' --data '{json}' {hook}").read()


def main():
    BASE_MESSAGE = '{"text":"\n' + \
        f'|----- Miss Minutes Report for {date.today()} START-----|\n' + \
        f'|=================================================|\n'

    user, passw, slack = dotloader()
    project_list = ['= "Darwin"', '= "VGP+"', '= "VGP"', '= "ASG"', '= "ERGA"', '= "Faculty"', '= "Other"']
    for i in project_list:
        print(f'---RUNNING PROJECT{i[3:-1]}---')
        proj_len, item_dict, ticket_other, ticket_rc, ticket_grit,\
        stat_today, stat_submitted, auth_jira = authorise(i, user, passw)
        message, empty = make_json(i, BASE_MESSAGE, item_dict, ticket_other, ticket_rc, ticket_grit, stat_today, stat_submitted)
        if proj_len <= 0:
            message = message + f'|=================================================|\n'

        message_new = new_tickets(i, auth_jira, message, empty)
        message_new_2 = fin_tickets(i, auth_jira, message_new, empty)

        BASE_MESSAGE += message_new_2

    final_message = BASE_MESSAGE + f'|----- Miss Minutes Report for {date.today()} END -----|' + \
                    '"}'
    print(final_message)
    post_it(final_message, slack)


if __name__ == '__main__':
    main()
